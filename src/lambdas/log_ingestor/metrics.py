"""CloudWatch custom metrics via boto3."""

from __future__ import annotations

import logging
from typing import Any

import boto3

from .config import Config

logger = logging.getLogger(__name__)

METRIC_BATCH_LIMIT = 20


class CloudWatchMetrics:
    def __init__(self, config: Config, cloudwatch_client: Any | None = None) -> None:
        self._config = config
        self._client = cloudwatch_client or boto3.client("cloudwatch")
        self._pending: list[dict[str, Any]] = []

    def record_invocation(self) -> None:
        self._add_metric("IngestorInvocations", 1)

    def record_logs_accepted(self, count: int) -> None:
        self._add_metric("IngestorLogsAccepted", count)

    def record_validation_errors(self, count: int) -> None:
        self._add_metric("IngestorValidationErrors", count)

    def record_enqueue_errors(self, count: int) -> None:
        self._add_metric("IngestorEnqueueErrors", count)

    def record_priority_routed(self, count: int) -> None:
        self._add_metric("IngestorPriorityRouted", count)

    def flush(self) -> None:
        if not self._pending:
            return

        metric_count = len(self._pending)
        logger.debug(
            "Flushing %s custom metrics to CloudWatch namespace=%s",
            metric_count,
            self._config.metrics_namespace,
        )
        for batch_start in range(0, len(self._pending), METRIC_BATCH_LIMIT):
            batch = self._pending[batch_start : batch_start + METRIC_BATCH_LIMIT]
            self._client.put_metric_data(
                Namespace=self._config.metrics_namespace,
                MetricData=batch,
            )
        self._pending.clear()

    def _add_metric(self, name: str, value: int) -> None:
        if not value:
            return

        self._pending.append(
            {
                "MetricName": name,
                "Value": value,
                "Unit": "Count",
                "Dimensions": [{"Name": "service", "Value": self._config.service_name}],
            }
        )
