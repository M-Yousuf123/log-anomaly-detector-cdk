import json
from unittest.mock import MagicMock

from log_ingestor.app import LogIngestorApp
from log_ingestor.config import Config
from log_ingestor.enricher import DefaultLogEnricher
from log_ingestor.errors import ErrorCode
from log_ingestor.handler import create_app
from log_ingestor.models import Route
from log_ingestor.response_builder import ResponseBuilder
from log_ingestor.router import DefaultLogRouter
from log_ingestor.validator import DefaultLogValidator

from factories import FakeMetrics, FakePublisher, VALID_LOG, api_event


def _build_app(
    config: Config,
    publisher: FakePublisher | None = None,
    metrics: FakeMetrics | None = None,
) -> LogIngestorApp:
    return LogIngestorApp(
        validator=DefaultLogValidator(),
        enricher=DefaultLogEnricher(),
        router=DefaultLogRouter(),
        publisher=publisher or FakePublisher(),
        metrics=metrics or FakeMetrics(),
        responses=ResponseBuilder(),
        config=config,
    )


def test_valid_single_log_accepted(config: Config) -> None:
    publisher = FakePublisher()
    app = _build_app(config, publisher)
    response = app.handle(api_event(VALID_LOG))

    assert response["statusCode"] == 202
    body = json.loads(response["body"])
    assert body["accepted"] == 1
    assert body["rejected"] == 0
    assert len(publisher.published) == 1
    assert publisher.published[0].route == Route.PRIORITY


def test_info_log_routes_to_main(config: Config) -> None:
    publisher = FakePublisher()
    app = _build_app(config, publisher)
    log = {**VALID_LOG, "level": "INFO", "message": "service healthy"}
    response = app.handle(api_event(log))

    assert response["statusCode"] == 202
    assert publisher.published[0].route == Route.MAIN


def test_batch_partial_failure(config: Config) -> None:
    publisher = FakePublisher()
    app = _build_app(config, publisher)
    response = app.handle(
        api_event(
            {
                "logs": [
                    VALID_LOG,
                    {"level": "INFO", "message": "missing fields", "timestamp": "2026-06-14T10:30:00Z"},
                ]
            }
        )
    )

    body = json.loads(response["body"])
    assert response["statusCode"] == 202
    assert body["accepted"] == 1
    assert body["rejected"] == 1
    assert body["errors"][0]["code"] == ErrorCode.VALIDATION_ERROR


def test_correlation_id_from_header(config: Config) -> None:
    app = _build_app(config)
    response = app.handle(api_event(VALID_LOG, headers={"X-Correlation-Id": "client-corr"}))
    body = json.loads(response["body"])
    assert body["correlation_id"] == "client-corr"


def test_sqs_failure_returns_503_and_metric(config: Config) -> None:
    metrics = FakeMetrics()
    app = _build_app(config, publisher=FakePublisher(fail=True), metrics=metrics)
    response = app.handle(api_event(VALID_LOG))

    assert response["statusCode"] == 503
    assert metrics.enqueue_errors == 1


def test_create_app_wires_dependencies(config: Config, mocker) -> None:
    mocker.patch("log_ingestor.publisher.boto3.client", return_value=MagicMock())
    mocker.patch("log_ingestor.metrics.boto3.client", return_value=MagicMock())
    app = create_app(config)
    assert isinstance(app.validator, DefaultLogValidator)
