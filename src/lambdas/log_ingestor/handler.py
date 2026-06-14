"""Thin Lambda entrypoint — wiring only."""

from __future__ import annotations

from typing import Any

from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.utilities.typing import LambdaContext

from .app import LogIngestorApp
from .config import Config, load_config
from .enricher import DefaultLogEnricher
from .metrics import CloudWatchMetrics
from .publisher import SqsPublisher
from .response_builder import ResponseBuilder
from .router import DefaultLogRouter
from .validator import DefaultLogValidator

logger = Logger()
tracer = Tracer()


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


@logger.inject_lambda_context
@tracer.capture_lambda_handler
def handler(event: dict[str, Any], context: LambdaContext) -> dict[str, Any]:
    return _get_app().handle(event)
