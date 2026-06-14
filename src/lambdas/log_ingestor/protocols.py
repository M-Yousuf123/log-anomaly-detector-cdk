"""Protocol interfaces for dependency injection and test doubles."""

from __future__ import annotations

from typing import Any, Protocol

from .models import EnrichedLog, InboundLog, IngestionResult, Route, ValidationItemError


class LogValidator(Protocol):
    def validate(self, raw: dict[str, Any], index: int) -> tuple[InboundLog | None, ValidationItemError | None]:
        """Validate a single raw log dict; return (log, error) — exactly one is non-None."""


class LogEnricher(Protocol):
    def enrich(self, log: InboundLog, correlation_id: str, route: Route) -> EnrichedLog:
        """Attach ingest metadata and routing decision to an accepted log."""


class LogRouter(Protocol):
    def route(self, log: InboundLog) -> Route:
        """Decide main vs priority queue for a validated log."""


class QueuePublisher(Protocol):
    def publish(self, logs: list[EnrichedLog]) -> None:
        """Publish enriched logs to the appropriate SQS queues; raise EnqueueError on failure."""


class MetricsEmitter(Protocol):
    def record_invocation(self) -> None: ...

    def record_logs_accepted(self, count: int) -> None: ...

    def record_validation_errors(self, count: int) -> None: ...

    def record_enqueue_errors(self, count: int) -> None: ...

    def record_priority_routed(self, count: int) -> None: ...

    def flush(self) -> None: ...
