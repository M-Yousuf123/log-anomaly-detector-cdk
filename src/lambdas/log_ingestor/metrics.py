"""CloudWatch custom metrics via aws-lambda-powertools."""

from __future__ import annotations

from aws_lambda_powertools import Metrics
from aws_lambda_powertools.metrics import MetricUnit

from .config import Config
from .protocols import MetricsEmitter


class CloudWatchMetrics:
    def __init__(self, config: Config, metrics: Metrics | None = None) -> None:
        self._metrics = metrics or Metrics(namespace=config.metrics_namespace, service=config.service_name)

    def record_invocation(self) -> None:
        self._metrics.add_metric(name="IngestorInvocations", unit=MetricUnit.Count, value=1)

    def record_logs_accepted(self, count: int) -> None:
        if count:
            self._metrics.add_metric(name="IngestorLogsAccepted", unit=MetricUnit.Count, value=count)

    def record_validation_errors(self, count: int) -> None:
        if count:
            self._metrics.add_metric(
                name="IngestorValidationErrors", unit=MetricUnit.Count, value=count
            )

    def record_enqueue_errors(self, count: int) -> None:
        if count:
            self._metrics.add_metric(name="IngestorEnqueueErrors", unit=MetricUnit.Count, value=count)

    def record_priority_routed(self, count: int) -> None:
        if count:
            self._metrics.add_metric(name="IngestorPriorityRouted", unit=MetricUnit.Count, value=count)

    def flush(self) -> None:
        self._metrics.flush_metrics()
