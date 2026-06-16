"""Enrich accepted logs with ingest metadata."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from .models import EnrichedLog, InboundLog, Route


class DefaultLogEnricher:
    def enrich(self, log: InboundLog, correlation_id: str, route: Route) -> EnrichedLog:
        return EnrichedLog(
            service_name=log.service_name,
            level=log.level,
            message=log.message,
            timestamp=log.timestamp,
            latency_ms=log.latency_ms,
            trace_id=log.trace_id,
            metadata=log.metadata,
            ingest_id=uuid4(),
            ingested_at=datetime.now(tz=UTC),
            correlation_id=correlation_id,
            route=route,
        )
