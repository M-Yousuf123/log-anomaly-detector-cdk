from log_ingestor.errors import ErrorCode
from log_ingestor.validator import DefaultLogValidator

from factories import VALID_LOG


def test_valid_log_passes(validator: DefaultLogValidator) -> None:
    log, error = validator.validate(VALID_LOG, 0)
    assert log is not None
    assert error is None
    assert log.service_name == "payment-api"


def test_missing_service_name_rejected(validator: DefaultLogValidator) -> None:
    payload = {**VALID_LOG}
    del payload["service_name"]
    log, error = validator.validate(payload, 0)
    assert log is None
    assert error is not None
    assert error.code == ErrorCode.VALIDATION_ERROR
    assert error.index == 0


def test_invalid_timestamp_rejected(validator: DefaultLogValidator) -> None:
    log, error = validator.validate({**VALID_LOG, "timestamp": "not-a-date"}, 2)
    assert log is None
    assert error is not None
    assert error.index == 2


def test_message_too_long_rejected(validator: DefaultLogValidator) -> None:
    log, error = validator.validate({**VALID_LOG, "message": "x" * 4097}, 0)
    assert log is None
    assert error is not None


def test_invalid_level_rejected(validator: DefaultLogValidator) -> None:
    log, error = validator.validate({**VALID_LOG, "level": "CRITICAL"}, 0)
    assert log is None
    assert error is not None
