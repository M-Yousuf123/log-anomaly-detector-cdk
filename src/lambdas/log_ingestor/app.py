"""Application orchestration — composes validator, enricher, router, publisher."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any

from .config import Config
from .errors import EnqueueError
from .models import EnrichedLog, InboundLog, IngestionResult, Route, ValidationItemError
from .protocols import LogEnricher, LogRouter, LogValidator, MetricsEmitter, QueuePublisher
from .response_builder import ResponseBuilder

logger = logging.getLogger(__name__)


@dataclass
class LogIngestorApp:
    validator: LogValidator
    enricher: LogEnricher
    router: LogRouter
    publisher: QueuePublisher
    metrics: MetricsEmitter
    responses: ResponseBuilder
    config: Config

    def handle(self, event: dict[str, Any]) -> dict[str, Any]:
        start = time.perf_counter()
        self.metrics.record_invocation()
        headers = event.get("headers") or {}
        correlation_id = self.responses.extract_correlation_id(headers)
        logger.info("Ingestion request started correlation_id=%s", correlation_id)

        raw_logs, parse_error = self.responses.parse_body(event.get("body"))
        errors: list[ValidationItemError] = [parse_error] if parse_error else []
        accepted_logs: list[InboundLog] = []

        if parse_error:
            logger.warning(
                "Request body parse failed correlation_id=%s reason=%s",
                correlation_id,
                parse_error.reason,
            )
        else:
            for index, raw in enumerate(raw_logs):
                log, error = self.validator.validate(raw, index)
                if log:
                    accepted_logs.append(log)
                elif error:
                    errors.append(error)

        enriched = self._enrich_batch(accepted_logs, correlation_id)
        enqueue_failed = False
        if enriched:
            try:
                self.publisher.publish(enriched)
            except EnqueueError as exc:
                enqueue_failed = True
                self.metrics.record_enqueue_errors(len(enriched))
                logger.error(
                    "Failed to enqueue logs correlation_id=%s count=%s reason=%s",
                    correlation_id,
                    len(enriched),
                    exc.reason,
                )

        priority_count = sum(1 for log in enriched if log.route == Route.PRIORITY)
        self.metrics.record_logs_accepted(len(enriched))
        self.metrics.record_validation_errors(len(errors))
        self.metrics.record_priority_routed(priority_count)
        self.metrics.flush()

        duration_ms = (time.perf_counter() - start) * 1000
        logger.info(
            "Ingestion complete correlation_id=%s batch_size=%s accepted=%s rejected=%s "
            "priority_routed=%s enqueue_failed=%s duration_ms=%s",
            correlation_id,
            len(raw_logs),
            len(enriched),
            len(errors),
            priority_count,
            enqueue_failed,
            round(duration_ms, 2),
        )
        for error in errors:
            logger.debug(
                "Validation error correlation_id=%s index=%s code=%s reason=%s",
                correlation_id,
                error.index,
                error.code,
                error.reason,
            )
        for enriched_log in enriched:
            logger.debug(
                "Log routed correlation_id=%s service_name=%s level=%s route=%s message_preview=%s",
                correlation_id,
                enriched_log.service_name,
                enriched_log.level,
                enriched_log.route,
                enriched_log.message[:100],
            )

        result = IngestionResult(
            accepted=len(enriched) if not enqueue_failed else 0,
            rejected=len(errors) + (len(enriched) if enqueue_failed else 0),
            correlation_id=correlation_id,
            errors=errors,
            enqueue_failed=enqueue_failed,
        )
        return self.responses.build_http_response(result)

    def _enrich_batch(self, logs: list[InboundLog], correlation_id: str) -> list[EnrichedLog]:
        return [
            self.enricher.enrich(log, correlation_id, self.router.route(log)) for log in logs
        ]
