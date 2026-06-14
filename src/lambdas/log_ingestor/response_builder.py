"""API Gateway HTTP API v2 request parsing and response mapping."""

from __future__ import annotations

import json
from typing import Any
from uuid import uuid4

from .errors import ErrorCode
from .models import IngestionResult, MAX_BATCH_SIZE, ValidationItemError


class ResponseBuilder:
    def parse_body(self, body: str | None) -> tuple[list[dict[str, Any]], ValidationItemError | None]:
        if not body:
            return [], ValidationItemError(
                index=0, code=ErrorCode.PARSE_ERROR, reason="Request body is required"
            )
        try:
            payload = json.loads(body)
        except json.JSONDecodeError as exc:
            return [], ValidationItemError(
                index=0, code=ErrorCode.PARSE_ERROR, reason=f"Invalid JSON: {exc.msg}"
            )

        # Batch of log objects
        if isinstance(payload, list):
            return self._validate_batch_size(payload)

        # Batch of log objects in a "logs" field
        if isinstance(payload, dict) and "logs" in payload:
            logs = payload["logs"]
            if not isinstance(logs, list):
                return [], ValidationItemError(
                    index=0, code=ErrorCode.PARSE_ERROR, reason="'logs' must be an array"
                )
            return self._validate_batch_size(logs)

        # Single log object
        if isinstance(payload, dict):
            return [payload], None

        return [], ValidationItemError(
            index=0, code=ErrorCode.PARSE_ERROR, reason="Body must be a log object or {'logs': [...]}"
        )

    def extract_correlation_id(self, headers: dict[str, str] | None) -> str:
        normalized = {k.lower(): v for k, v in (headers or {}).items()}
        header_value = normalized.get("x-correlation-id")
        if header_value and header_value.strip():
            return header_value.strip()
        return str(uuid4())

    def build_http_response(self, result: IngestionResult) -> dict[str, Any]:
        body = {
            "accepted": result.accepted,
            "rejected": result.rejected,
            "correlation_id": result.correlation_id,
            "errors": [error.model_dump() for error in result.errors],
        }
        status_code = self._status_code(result)
        return {
            "statusCode": status_code,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(body),
        }

    @staticmethod
    def _status_code(result: IngestionResult) -> int:
        if result.enqueue_failed:
            return 503
        if result.accepted > 0:
            return 202
        return 400

    @staticmethod
    def _validate_batch_size(
        logs: list[Any],
    ) -> tuple[list[dict[str, Any]], ValidationItemError | None]:
        if len(logs) > MAX_BATCH_SIZE:
            return [], ValidationItemError(
                index=0,
                code=ErrorCode.VALIDATION_ERROR,
                reason=f"Batch size exceeds maximum of {MAX_BATCH_SIZE}",
            )
        if not all(isinstance(item, dict) for item in logs):
            return [], ValidationItemError(
                index=0,
                code=ErrorCode.PARSE_ERROR,
                reason="Each log entry must be a JSON object",
            )
        return logs, None
