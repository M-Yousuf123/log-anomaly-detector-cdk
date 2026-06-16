"""Priority vs main queue routing decisions."""

from __future__ import annotations

import re

from .models import InboundLog, LogLevel, Route

PRIORITY_LEVELS = frozenset({LogLevel.WARN, LogLevel.ERROR})

PRIORITY_MESSAGE_PATTERNS = re.compile(
    r"timeout|exception|fatal|5xx|unavailable|denied",
    re.IGNORECASE,
)


class DefaultLogRouter:
    """Route to priority FIFO when level is WARN/ERROR or message matches alert patterns."""

    def route(self, log: InboundLog) -> Route:
        if log.level in PRIORITY_LEVELS:
            return Route.PRIORITY
        if PRIORITY_MESSAGE_PATTERNS.search(log.message):
            return Route.PRIORITY
        return Route.MAIN
