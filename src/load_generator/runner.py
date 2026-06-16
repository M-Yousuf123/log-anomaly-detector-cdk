from __future__ import annotations

import signal
import time
import uuid
from typing import Any

from load_generator.constants import MAX_BATCH_SIZE
from load_generator.generator import SyntheticLogGenerator
from load_generator.models import GeneratorConfig, LogSender, RunState, SendStats, TrafficPhase
from load_generator.scheduler import TrafficScheduler


def run_load_generator(
    sender: LogSender,
    config: GeneratorConfig,
    duration_s: float | None,
    report_interval_s: float,
) -> SendStats:
    generator = SyntheticLogGenerator(config)
    scheduler = TrafficScheduler(config)
    stats = SendStats()
    state = RunState()

    def handle_stop(signum: int, _frame: Any) -> None:
        del signum
        state.stop_requested = True

    signal.signal(signal.SIGINT, handle_stop)
    signal.signal(signal.SIGTERM, handle_stop)

    last_report = time.monotonic()
    next_send_at = time.monotonic()

    while not state.stop_requested:
        elapsed = time.monotonic() - state.started_at
        if duration_s is not None and elapsed >= duration_s:
            break

        phase, target_rate = scheduler.current_phase(elapsed)
        if target_rate <= 0:
            time.sleep(0.1)
            continue

        batch_size = min(config.batch_size, MAX_BATCH_SIZE)
        interval = batch_size / target_rate
        now = time.monotonic()
        if now < next_send_at:
            time.sleep(min(next_send_at - now, 0.05))
            continue

        logs = generator.next_batch(batch_size, phase, state)
        correlation_id = str(uuid.uuid4())
        accepted, rejected, error = sender.send_batch(logs, correlation_id)

        stats.requests_sent += 1
        stats.events_sent += len(logs)
        stats.events_accepted += accepted
        stats.events_rejected += rejected
        if error:
            stats.http_errors += 1
            stats.last_error = error

        next_send_at = max(next_send_at + interval, time.monotonic())

        if time.monotonic() - last_report >= report_interval_s:
            print_status(elapsed, phase, target_rate, stats, state)
            last_report = time.monotonic()

    print_status(time.monotonic() - state.started_at, TrafficPhase.BASELINE, 0, stats, state, final=True)
    return stats


def print_status(
    elapsed_s: float,
    phase: TrafficPhase,
    target_rate: float,
    stats: SendStats,
    state: RunState,
    *,
    final: bool = False,
) -> None:
    label = "FINAL" if final else "STATUS"
    print(
        f"[{label}] t={elapsed_s:0.1f}s phase={phase.value} "
        f"target_rate={target_rate:0.1f}/s "
        f"sent={stats.events_sent} accepted={stats.events_accepted} "
        f"rejected={stats.events_rejected} rare={state.rare_injected} "
        f"http_errors={stats.http_errors}",
        flush=True,
    )
    if stats.last_error:
        print(f"  last_error={stats.last_error}", flush=True)
