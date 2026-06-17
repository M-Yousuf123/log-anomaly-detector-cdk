"""Environment-based configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    main_queue_url: str
    priority_queue_url: str
    max_batch_size: int = 100
    sqs_max_retries: int = 3
    sqs_batch_size: int = 10
    metrics_namespace: str = "LogAnomalyDetector"
    service_name: str = "log-ingestor"


def load_config() -> Config:
    main_queue_url = os.environ.get("MAIN_QUEUE_URL", "")
    priority_queue_url = os.environ.get("PRIORITY_QUEUE_URL", "")
    if not main_queue_url or not priority_queue_url:
        raise RuntimeError("MAIN_QUEUE_URL and PRIORITY_QUEUE_URL must be set")
    return Config(
        main_queue_url=main_queue_url,
        priority_queue_url=priority_queue_url,
        service_name=os.environ.get("SERVICE_NAME", "log-ingestor"),
    )
