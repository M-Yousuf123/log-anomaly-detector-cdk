from unittest.mock import MagicMock

from log_ingestor.config import Config
from log_ingestor.metrics import CloudWatchMetrics


def test_metrics_emit_all_counters(config: Config) -> None:
    cloudwatch = MagicMock()
    metrics = CloudWatchMetrics(config, cloudwatch_client=cloudwatch)
    metrics.record_invocation()
    metrics.record_logs_accepted(3)
    metrics.record_validation_errors(1)
    metrics.record_enqueue_errors(2)
    metrics.record_priority_routed(1)
    metrics.flush()

    cloudwatch.put_metric_data.assert_called_once()
    call_kwargs = cloudwatch.put_metric_data.call_args.kwargs
    assert call_kwargs["Namespace"] == config.metrics_namespace
    assert len(call_kwargs["MetricData"]) == 5
