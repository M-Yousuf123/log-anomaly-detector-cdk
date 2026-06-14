"""Input validation for inbound log events."""

from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from .errors import ErrorCode
from .models import InboundLog, ValidationItemError
from .protocols import LogValidator


class DefaultLogValidator:
    def validate(
        self, raw: dict[str, Any], index: int
    ) -> tuple[InboundLog | None, ValidationItemError | None]:
        try:
            return InboundLog.model_validate(raw), None
        except ValidationError as exc:
            return None, ValidationItemError(
                index=index,
                code=ErrorCode.VALIDATION_ERROR,
                reason=_format_validation_error(exc),
            )


def _format_validation_error(exc: ValidationError) -> str:
    messages = [f"{'.'.join(str(part) for part in err['loc'])}: {err['msg']}" for err in exc.errors()]
    return "; ".join(messages)
