from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Protocol


class Transport(StrEnum):
    HTTP = "http"
    LAMBDA = "lambda"


class TrafficPhase(StrEnum):
    BASELINE = "baseline"
    SPIKE = "spike"
    ERROR_SURGE = "error_surge"


@dataclass(frozen=True)
class GeneratorConfig:
    baseline_rate: float
    batch_size: int
    spike_interval_s: float
    spike_multiplier: float
    spike_duration_s: float
    error_surge_interval_s: float
    error_surge_duration_s: float
    error_surge_fraction: float
    rare_event_interval: int
    seed: int | None = None


@dataclass
class SendStats:
    requests_sent: int = 0
    events_sent: int = 0
    events_accepted: int = 0
    events_rejected: int = 0
    http_errors: int = 0
    last_error: str | None = None


@dataclass
class RunState:
    started_at: float = field(default_factory=time.monotonic)
    events_generated: int = 0
    rare_injected: int = 0
    stop_requested: bool = False


class LogSender(Protocol):
    def send_batch(
        self, logs: list[dict[str, Any]], correlation_id: str
    ) -> tuple[int, int, str | None]:
        """Return (accepted, rejected, error_message)."""
