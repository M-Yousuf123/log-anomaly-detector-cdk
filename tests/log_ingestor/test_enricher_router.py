from typing import Any
from uuid import UUID

from log_ingestor.enricher import DefaultLogEnricher
from log_ingestor.models import InboundLog, Route
from log_ingestor.router import DefaultLogRouter

from factories import VALID_LOG


def _inbound(**overrides: Any) -> InboundLog:
    return InboundLog.model_validate({**VALID_LOG, **overrides})


def test_error_level_routes_to_priority(router: DefaultLogRouter) -> None:
    assert router.route(_inbound(level="ERROR")) == Route.PRIORITY


def test_warn_level_routes_to_priority(router: DefaultLogRouter) -> None:
    assert router.route(_inbound(level="WARN")) == Route.PRIORITY


def test_info_level_routes_to_main(router: DefaultLogRouter) -> None:
    assert router.route(_inbound(level="INFO", message="service started successfully")) == Route.MAIN


def test_timeout_message_routes_to_priority(router: DefaultLogRouter) -> None:
    assert router.route(_inbound(level="INFO", message="Connection TIMEOUT occurred")) == Route.PRIORITY


def test_enricher_adds_required_fields(enricher: DefaultLogEnricher) -> None:
    log = _inbound(level="INFO")
    enriched = enricher.enrich(log, "corr-1", Route.MAIN)

    assert isinstance(enriched.ingest_id, UUID)
    assert enriched.correlation_id == "corr-1"
    assert enriched.route == Route.MAIN
    assert enriched.schema_version == "1.0"
    assert enriched.ingested_at.tzinfo is not None
