"""Shared test data, constants, and fakes for log_ingestor tests."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from log_ingestor.errors import EnqueueError
from log_ingestor.models import EnrichedLog
from log_ingestor.protocols import MetricsEmitter, QueuePublisher

TEST_ACCOUNT_ID = "123"
TEST_REGION = "us-east-1"
TEST_MAIN_QUEUE_URL = f"https://sqs.{TEST_REGION}.amazonaws.com/{TEST_ACCOUNT_ID}/main"
TEST_PRIORITY_QUEUE_URL = (
    f"https://sqs.{TEST_REGION}.amazonaws.com/{TEST_ACCOUNT_ID}/priority.fifo"
)

VALID_LOG: dict[str, Any] = {
    "service_name": "payment-api",
    "level": "ERROR",
    "message": "Connection timeout to db-primary",
    "timestamp": "2026-06-14T10:30:00Z",
    "latency_ms": 842,
    "trace_id": "abc-123",
    "metadata": {"region": "us-east-1"},
}


def api_event(body: dict[str, Any], headers: dict[str, str] | None = None) -> dict[str, Any]:
    return {
        "requestContext": {"requestId": "req-1"},
        "headers": headers or {},
        "body": json.dumps(body),
    }


@dataclass
class FakeMetrics(MetricsEmitter):
    invocations: int = 0
    accepted: int = 0
    validation_errors: int = 0
    enqueue_errors: int = 0
    priority_routed: int = 0

    def record_invocation(self) -> None:
        self.invocations += 1

    def record_logs_accepted(self, count: int) -> None:
        self.accepted += count

    def record_validation_errors(self, count: int) -> None:
        self.validation_errors += count

    def record_enqueue_errors(self, count: int) -> None:
        self.enqueue_errors += count

    def record_priority_routed(self, count: int) -> None:
        self.priority_routed += count

    def flush(self) -> None:
        return None


@dataclass
class FakePublisher(QueuePublisher):
    published: list[EnrichedLog] = field(default_factory=list)
    fail: bool = False

    def publish(self, logs: list[EnrichedLog]) -> None:
        if self.fail:
            raise EnqueueError("SQS unavailable")
        self.published.extend(logs)
