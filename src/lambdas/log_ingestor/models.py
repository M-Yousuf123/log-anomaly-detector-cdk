"""Pydantic schemas for inbound and enriched log events."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


SCHEMA_VERSION = "1.0"
MAX_MESSAGE_LENGTH = 4096
MAX_BATCH_SIZE = 100


class LogLevel(StrEnum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARN = "WARN"
    ERROR = "ERROR"


class Route(StrEnum):
    MAIN = "main"
    PRIORITY = "priority"


class InboundLog(BaseModel):
    """Log event submitted by a producer."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    service_name: str = Field(min_length=1)
    level: LogLevel
    message: str = Field(min_length=1, max_length=MAX_MESSAGE_LENGTH)
    timestamp: datetime
    latency_ms: int | None = Field(default=None, ge=0)
    trace_id: str | None = None
    metadata: dict[str, Any] | None = None

    @field_validator("timestamp")
    @classmethod
    def timestamp_must_be_utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("timestamp must include UTC timezone (ISO-8601 with Z or offset)")
        return value


class EnrichedLog(BaseModel):
    """Log event enriched for downstream SQS consumers."""

    model_config = ConfigDict(extra="forbid")

    service_name: str
    level: LogLevel
    message: str
    timestamp: datetime
    latency_ms: int | None = None
    trace_id: str | None = None
    metadata: dict[str, Any] | None = None
    ingest_id: UUID
    ingested_at: datetime
    correlation_id: str
    route: Route
    schema_version: str = SCHEMA_VERSION


class ValidationItemError(BaseModel):
    index: int
    code: str
    reason: str


class IngestionResult(BaseModel):
    accepted: int
    rejected: int
    correlation_id: str
    errors: list[ValidationItemError]
    enqueue_failed: bool = False
