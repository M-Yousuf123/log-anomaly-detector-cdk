from __future__ import annotations

import argparse
import sys

import boto3

from load_generator.config import load_dotenv
from load_generator.constants import DEFAULT_LAMBDA_NAME, MAX_BATCH_SIZE
from load_generator.models import GeneratorConfig, Transport
from load_generator.runner import run_load_generator
from load_generator.senders import build_sender


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate synthetic log traffic against the log ingestor API.",
    )
    parser.add_argument("--region", default=boto3.Session().region_name or "us-east-1")
    parser.add_argument(
        "--api-url",
        help="Ingest HTTP API base URL. Overrides INGEST_API_URL from .env when set.",
    )
    parser.add_argument(
        "--transport",
        choices=[Transport.HTTP.value, Transport.LAMBDA.value],
        default=Transport.HTTP.value,
        help="Send through API Gateway (http) or invoke the ingestor Lambda directly.",
    )
    parser.add_argument("--lambda-name", default=DEFAULT_LAMBDA_NAME)
    parser.add_argument("--timeout", type=float, default=30.0, help="HTTP/Lambda request timeout in seconds.")
    parser.add_argument("--duration", type=float, default=300.0, help="Run time in seconds. Use 0 for unlimited.")
    parser.add_argument("--report-interval", type=float, default=10.0, help="Progress log interval in seconds.")
    parser.add_argument("--baseline-rate", type=float, default=10.0, help="Baseline events per second.")
    parser.add_argument("--batch-size", type=int, default=10, help="Events per request (max 100).")
    parser.add_argument("--spike-interval", type=float, default=120.0, help="Seconds between traffic spikes.")
    parser.add_argument("--spike-multiplier", type=float, default=5.0, help="Rate multiplier during spikes.")
    parser.add_argument("--spike-duration", type=float, default=30.0, help="Spike window length in seconds.")
    parser.add_argument("--error-surge-interval", type=float, default=180.0, help="Seconds between error surges.")
    parser.add_argument("--error-surge-duration", type=float, default=45.0, help="Error surge window in seconds.")
    parser.add_argument(
        "--error-surge-fraction",
        type=float,
        default=0.6,
        help="Fraction of events emitted as WARN/ERROR during an error surge.",
    )
    parser.add_argument(
        "--rare-event-interval",
        type=int,
        default=250,
        help="Inject a rare anomalous message every N generated events (0 disables).",
    )
    parser.add_argument("--seed", type=int, help="Random seed for reproducible traffic.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    load_dotenv()
    args = parse_args(argv)
    if args.batch_size < 1 or args.batch_size > MAX_BATCH_SIZE:
        print(f"--batch-size must be between 1 and {MAX_BATCH_SIZE}", file=sys.stderr)
        return 2
    if not 0 <= args.error_surge_fraction <= 1:
        print("--error-surge-fraction must be between 0 and 1", file=sys.stderr)
        return 2

    config = GeneratorConfig(
        baseline_rate=args.baseline_rate,
        batch_size=args.batch_size,
        spike_interval_s=args.spike_interval,
        spike_multiplier=args.spike_multiplier,
        spike_duration_s=args.spike_duration,
        error_surge_interval_s=args.error_surge_interval,
        error_surge_duration_s=args.error_surge_duration,
        error_surge_fraction=args.error_surge_fraction,
        rare_event_interval=args.rare_event_interval,
        seed=args.seed,
    )

    try:
        sender = build_sender(args)
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    duration = None if args.duration == 0 else args.duration
    stats = run_load_generator(
        sender=sender,
        config=config,
        duration_s=duration,
        report_interval_s=args.report_interval,
    )
    return 1 if stats.http_errors and stats.events_accepted == 0 else 0


if __name__ == "__main__":
    raise SystemExit(main())
