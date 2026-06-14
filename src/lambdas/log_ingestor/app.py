"""Application orchestration — composes validator, enricher, router, publisher."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

from aws_lambda_powertools import Logger

from .config import Config
from .errors import EnqueueError
from .models import EnrichedLog, InboundLog, IngestionResult, Route, ValidationItemError
from .protocols import LogEnricher, LogRouter, LogValidator, MetricsEmitter, QueuePublisher
from .response_builder import ResponseBuilder

logger = Logger()


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
        raw_logs, parse_error = self.responses.parse_body(event.get("body"))
        errors: list[ValidationItemError] = [parse_error] if parse_error else []
        accepted_logs: list[InboundLog] = []

        if not parse_error:
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
            except EnqueueError:
                enqueue_failed = True
                self.metrics.record_enqueue_errors(len(enriched))

        priority_count = sum(1 for log in enriched if log.route == Route.PRIORITY)
        self.metrics.record_logs_accepted(len(enriched))
        self.metrics.record_validation_errors(len(errors))
        self.metrics.record_priority_routed(priority_count)
        self.metrics.flush()

        duration_ms = (time.perf_counter() - start) * 1000
        logger.info(
            "Ingestion complete",
            extra={
                "correlation_id": correlation_id,
                "batch_size": len(raw_logs),
                "accepted": len(enriched),
                "rejected": len(errors),
                "duration_ms": round(duration_ms, 2),
            },
        )
        for enriched_log in enriched:
            logger.debug(
                "Log routed",
                extra={
                    "correlation_id": correlation_id,
                    "service_name": enriched_log.service_name,
                    "level": enriched_log.level,
                    "route": enriched_log.route,
                    "message_preview": enriched_log.message[:100],
                },
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
