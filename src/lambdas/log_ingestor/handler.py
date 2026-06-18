"""Thin Lambda entrypoint — wiring only."""

from __future__ import annotations

import logging
from typing import Any

from .app import LogIngestorApp

logger = logging.getLogger(__name__)
from .config import Config, load_config
from .enricher import DefaultLogEnricher
from .metrics import CloudWatchMetrics
from .publisher import SqsPublisher
from .response_builder import ResponseBuilder
from .router import DefaultLogRouter
from .validator import DefaultLogValidator


def create_app(config: Config | None = None) -> LogIngestorApp:
    resolved = config or load_config()
    return LogIngestorApp(
        validator=DefaultLogValidator(),
        enricher=DefaultLogEnricher(),
        router=DefaultLogRouter(),
        publisher=SqsPublisher(resolved),
        metrics=CloudWatchMetrics(resolved),
        responses=ResponseBuilder(),
        config=resolved,
    )


_app: LogIngestorApp | None = None


def _get_app() -> LogIngestorApp:
    global _app
    if _app is None:
        _app = create_app()
    return _app


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    request_id = getattr(context, "aws_request_id", None)
    logger.debug("Lambda invoked request_id=%s", request_id)
    return _get_app().handle(event)
