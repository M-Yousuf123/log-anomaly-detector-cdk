import json

from log_ingestor.models import IngestionResult, ValidationItemError
from log_ingestor.response_builder import ResponseBuilder


def test_extract_correlation_id_from_header() -> None:
    builder = ResponseBuilder()
    correlation_id = builder.extract_correlation_id({"X-Correlation-Id": "existing-id"})
    assert correlation_id == "existing-id"


def test_extract_correlation_id_generated_when_missing() -> None:
    builder = ResponseBuilder()
    correlation_id = builder.extract_correlation_id({})
    assert len(correlation_id) == 36


def test_parse_single_log_object() -> None:
    builder = ResponseBuilder()
    body = json.dumps({"service_name": "api", "level": "INFO", "message": "ok", "timestamp": "2026-06-14T10:30:00Z"})
    logs, error = builder.parse_body(body)
    assert error is None
    assert len(logs) == 1


def test_parse_batch_logs_wrapper() -> None:
    builder = ResponseBuilder()
    body = json.dumps({"logs": [{"service_name": "api", "level": "INFO", "message": "ok", "timestamp": "2026-06-14T10:30:00Z"}]})
    logs, error = builder.parse_body(body)
    assert error is None
    assert len(logs) == 1


def test_parse_invalid_json() -> None:
    builder = ResponseBuilder()
    logs, error = builder.parse_body("{bad")
    assert logs == []
    assert error is not None


def test_build_http_202_when_accepted() -> None:
    builder = ResponseBuilder()
    response = builder.build_http_response(
        IngestionResult(accepted=1, rejected=0, correlation_id="c1", errors=[])
    )
    assert response["statusCode"] == 202


def test_build_http_400_when_all_rejected() -> None:
    builder = ResponseBuilder()
    response = builder.build_http_response(
        IngestionResult(
            accepted=0,
            rejected=1,
            correlation_id="c1",
            errors=[ValidationItemError(index=0, code="VALIDATION_ERROR", reason="bad")],
        )
    )
    assert response["statusCode"] == 400


def test_build_http_503_on_enqueue_failure() -> None:
    builder = ResponseBuilder()
    response = builder.build_http_response(
        IngestionResult(accepted=0, rejected=1, correlation_id="c1", errors=[], enqueue_failed=True)
    )
    assert response["statusCode"] == 503
