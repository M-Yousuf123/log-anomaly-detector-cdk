"""SQS batch publish with retry and FIFO support."""

from __future__ import annotations

import logging
import time
from typing import Any, cast

import boto3
from botocore.exceptions import ClientError

from .config import Config
from .errors import EnqueueError
from .models import EnrichedLog, Route

logger = logging.getLogger(__name__)

SQS_BATCH_LIMIT = 10
RETRYABLE_ERROR_CODES = frozenset(
    {
        "ThrottlingException",
        "RequestThrottled",
        "ServiceUnavailable",
        "InternalError",
        "InternalFailure",
        "TooManyRequestsException",
    }
)


class SqsPublisher:
    def __init__(self, config: Config, sqs_client: Any | None = None) -> None:
        self._config = config
        self._sqs: Any = sqs_client or boto3.client("sqs")

    def publish(self, logs: list[EnrichedLog]) -> None:
        if not logs:
            return

        by_route: dict[Route, list[EnrichedLog]] = {Route.MAIN: [], Route.PRIORITY: []}
        for log in logs:
            by_route[log.route].append(log)

        for route, route_logs in by_route.items():
            if route_logs:
                queue_url = (
                    self._config.priority_queue_url
                    if route == Route.PRIORITY
                    else self._config.main_queue_url
                )
                logger.debug(
                    "Publishing %s logs to %s queue url=%s",
                    len(route_logs),
                    route.value,
                    queue_url,
                )
                self._publish_to_queue(queue_url, route_logs, fifo=route == Route.PRIORITY)

    def _publish_to_queue(
        self, queue_url: str, logs: list[EnrichedLog], *, fifo: bool
    ) -> None:
        for batch_start in range(0, len(logs), SQS_BATCH_LIMIT):
            batch = logs[batch_start : batch_start + SQS_BATCH_LIMIT]
            if len(batch) == 1:
                log = batch[0]
                self._send_with_retry(
                    lambda url=queue_url, entry=log, is_fifo=fifo: self._send_single(
                        url, entry, fifo=is_fifo
                    )
                )
            else:
                self._send_with_retry(
                    lambda url=queue_url, entries=batch, is_fifo=fifo: self._send_batch(
                        url, entries, fifo=is_fifo
                    )
                )

    def _send_single(self, queue_url: str, log: EnrichedLog, *, fifo: bool) -> dict[str, Any]:
        params: dict[str, Any] = {
            "QueueUrl": queue_url,
            "MessageBody": log.model_dump_json(),
        }
        if fifo:
            params["MessageGroupId"] = log.service_name
            params["MessageDeduplicationId"] = str(log.ingest_id)
        return cast(dict[str, Any], self._sqs.send_message(**params))

    def _send_batch(self, queue_url: str, logs: list[EnrichedLog], *, fifo: bool) -> dict[str, Any]:
        entries = []
        for index, log in enumerate(logs):
            entry: dict[str, Any] = {
                "Id": str(index),
                "MessageBody": log.model_dump_json(),
            }
            if fifo:
                entry["MessageGroupId"] = log.service_name
                entry["MessageDeduplicationId"] = str(log.ingest_id)
            entries.append(entry)
        return cast(dict[str, Any], self._sqs.send_message_batch(QueueUrl=queue_url, Entries=entries))

    def _send_with_retry(self, send_fn: Any) -> None:
        last_error: Exception | None = None
        for attempt in range(self._config.sqs_max_retries):
            try:
                response = send_fn()
                if self._has_batch_failures(response):
                    failed = response.get("Failed", [])
                    logger.error(
                        "SQS batch returned partial failures failed_count=%s details=%s",
                        len(failed),
                        failed,
                    )
                    raise EnqueueError("SQS batch returned partial failures")
                return
            except ClientError as exc:
                last_error = exc
                error_code = exc.response.get("Error", {}).get("Code", "")
                if not self._is_retryable(exc) or attempt == self._config.sqs_max_retries - 1:
                    logger.error(
                        "SQS send failed attempt=%s/%s error_code=%s",
                        attempt + 1,
                        self._config.sqs_max_retries,
                        error_code,
                    )
                    break
                logger.warning(
                    "Retryable SQS error attempt=%s/%s error_code=%s",
                    attempt + 1,
                    self._config.sqs_max_retries,
                    error_code,
                )
                time.sleep(2**attempt * 0.1)
            except EnqueueError:
                raise
            except Exception as exc:
                last_error = exc
                logger.error("Unexpected SQS publish error attempt=%s", attempt + 1, exc_info=exc)
                break

        reason = str(last_error) if last_error else "unknown SQS error"
        raise EnqueueError(reason) from last_error

    @staticmethod
    def _is_retryable(exc: ClientError) -> bool:
        code = exc.response.get("Error", {}).get("Code", "")
        return code in RETRYABLE_ERROR_CODES

    @staticmethod
    def _has_batch_failures(response: dict[str, Any]) -> bool:
        failed = response.get("Failed")
        return isinstance(failed, list) and len(failed) > 0
