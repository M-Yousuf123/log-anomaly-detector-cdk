from log_ingestor.config import Config
from log_ingestor.metrics import CloudWatchMetrics


def test_metrics_emit_all_counters(config: Config) -> None:
    metrics = CloudWatchMetrics(config)
    metrics.record_invocation()
    metrics.record_logs_accepted(3)
    metrics.record_validation_errors(1)
    metrics.record_enqueue_errors(2)
    metrics.record_priority_routed(1)
    metrics.flush()
