from __future__ import annotations

import random
import uuid
from datetime import UTC, datetime
from typing import Any

from load_generator.constants import ERROR_MESSAGES, NORMAL_MESSAGES, RARE_MESSAGES, SERVICES
from load_generator.models import GeneratorConfig, RunState, TrafficPhase


class SyntheticLogGenerator:
    def __init__(self, config: GeneratorConfig) -> None:
        self._config = config
        self._rng = random.Random(config.seed)

    def next_batch(
        self,
        count: int,
        phase: TrafficPhase,
        state: RunState,
    ) -> list[dict[str, Any]]:
        logs: list[dict[str, Any]] = []
        for _ in range(count):
            state.events_generated += 1
            if self._should_inject_rare(state):
                logs.append(self._build_rare_event())
                state.rare_injected += 1
                continue
            if phase == TrafficPhase.ERROR_SURGE and self._rng.random() < self._config.error_surge_fraction:
                logs.append(self._build_error_event())
                continue
            logs.append(self._build_normal_event())
        return logs

    def _should_inject_rare(self, state: RunState) -> bool:
        interval = self._config.rare_event_interval
        return interval > 0 and state.events_generated % interval == 0

    def _build_normal_event(self) -> dict[str, Any]:
        return self._build_event(
            level=self._rng.choice(("DEBUG", "INFO", "INFO", "INFO")),
            message=self._rng.choice(NORMAL_MESSAGES),
            latency_ms=self._rng.randint(5, 120),
        )

    def _build_error_event(self) -> dict[str, Any]:
        return self._build_event(
            level=self._rng.choice(("WARN", "ERROR", "ERROR")),
            message=self._rng.choice(ERROR_MESSAGES),
            latency_ms=self._rng.randint(500, 5000),
        )

    def _build_rare_event(self) -> dict[str, Any]:
        template = self._rng.choice(RARE_MESSAGES)
        message = template.format(
            sku=self._rng.randint(1000, 9999),
            partition=self._rng.randint(0, 31),
        )
        return self._build_event(
            level="ERROR",
            message=message,
            latency_ms=self._rng.randint(800, 9000),
            metadata={"anomaly_probe": True, "probe_id": str(uuid.uuid4())},
        )

    def _build_event(
        self,
        *,
        level: str,
        message: str,
        latency_ms: int,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        event: dict[str, Any] = {
            "service_name": self._rng.choice(SERVICES),
            "level": level,
            "message": message,
            "timestamp": datetime.now(tz=UTC).isoformat().replace("+00:00", "Z"),
            "latency_ms": latency_ms,
            "trace_id": str(uuid.uuid4()),
        }
        if metadata is not None:
            event["metadata"] = metadata
        return event
