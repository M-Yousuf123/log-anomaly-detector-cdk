from __future__ import annotations

from load_generator.models import GeneratorConfig, TrafficPhase


class TrafficScheduler:
    def __init__(self, config: GeneratorConfig) -> None:
        self._config = config

    def current_phase(self, elapsed_s: float) -> tuple[TrafficPhase, float]:
        if self._in_window(
            elapsed_s,
            self._config.error_surge_interval_s,
            self._config.error_surge_duration_s,
        ):
            return TrafficPhase.ERROR_SURGE, self._config.baseline_rate

        if self._in_window(
            elapsed_s,
            self._config.spike_interval_s,
            self._config.spike_duration_s,
        ):
            return TrafficPhase.SPIKE, self._config.baseline_rate * self._config.spike_multiplier

        return TrafficPhase.BASELINE, self._config.baseline_rate

    @staticmethod
    def _in_window(elapsed_s: float, interval_s: float, duration_s: float) -> bool:
        if interval_s <= 0 or duration_s <= 0:
            return False
        cycle_position = elapsed_s % interval_s
        return cycle_position < duration_s
