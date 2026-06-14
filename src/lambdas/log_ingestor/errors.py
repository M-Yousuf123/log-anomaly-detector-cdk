"""Domain exceptions and error codes for the log ingestor."""

from __future__ import annotations

from enum import StrEnum


class ErrorCode(StrEnum):
    VALIDATION_ERROR = "VALIDATION_ERROR"
    PARSE_ERROR = "PARSE_ERROR"
    ENQUEUE_ERROR = "ENQUEUE_ERROR"


class IngestorError(Exception):
    """Base exception for ingestor domain errors."""

    def __init__(self, code: ErrorCode, reason: str) -> None:
        self.code = code
        self.reason = reason
        super().__init__(reason)


class EnqueueError(IngestorError):
    """Raised when SQS publish fails after retries."""

    def __init__(self, reason: str) -> None:
        super().__init__(ErrorCode.ENQUEUE_ERROR, reason)
