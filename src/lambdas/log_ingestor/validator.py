"""Input validation for inbound log events."""

from __future__ import annotations

import logging
from typing import Any

from pydantic import ValidationError

from .errors import ErrorCode
from .models import InboundLog, ValidationItemError

logger = logging.getLogger(__name__)


class DefaultLogValidator:
    def validate(
        self, raw: dict[str, Any], index: int
    ) -> tuple[InboundLog | None, ValidationItemError | None]:
        try:
            return InboundLog.model_validate(raw), None
        except ValidationError as exc:
            reason = _format_validation_error(exc)
            logger.debug("Log validation failed index=%s reason=%s", index, reason)
            return None, ValidationItemError(
                index=index,
                code=ErrorCode.VALIDATION_ERROR,
                reason=reason,
            )


def _format_validation_error(exc: ValidationError) -> str:
    messages = [f"{'.'.join(str(part) for part in err['loc'])}: {err['msg']}" for err in exc.errors()]
    return "; ".join(messages)
