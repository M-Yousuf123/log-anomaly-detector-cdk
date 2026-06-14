from typing import Any
from unittest.mock import MagicMock

import pytest
from botocore.exceptions import ClientError

from log_ingestor.config import Config
from log_ingestor.enricher import DefaultLogEnricher
from log_ingestor.errors import EnqueueError
from log_ingestor.models import InboundLog, Route
from log_ingestor.publisher import SqsPublisher

from factories import VALID_LOG


def _enriched(route: Route = Route.PRIORITY) -> Any:
    log = InboundLog.model_validate(VALID_LOG)
    return DefaultLogEnricher().enrich(log, "corr-1", route)


def test_single_priority_log_uses_fifo_attributes(config: Config, sqs_client: MagicMock) -> None:
    publisher = SqsPublisher(config, sqs_client)
    enriched = _enriched(Route.PRIORITY)

    publisher.publish([enriched])

    sqs_client.send_message.assert_called_once()
    kwargs = sqs_client.send_message.call_args.kwargs
    assert kwargs["QueueUrl"] == config.priority_queue_url
    assert kwargs["MessageGroupId"] == "payment-api"
    assert kwargs["MessageDeduplicationId"] == str(enriched.ingest_id)


def test_info_log_uses_main_queue(config: Config, sqs_client: MagicMock) -> None:
    publisher = SqsPublisher(config, sqs_client)
    info_log = InboundLog.model_validate({**VALID_LOG, "level": "INFO", "message": "ok"})
    enriched = DefaultLogEnricher().enrich(info_log, "corr-1", Route.MAIN)

    publisher.publish([enriched])

    sqs_client.send_message.assert_called_once()
    assert sqs_client.send_message.call_args.kwargs["QueueUrl"] == config.main_queue_url
    assert "MessageGroupId" not in sqs_client.send_message.call_args.kwargs


def test_batch_uses_send_message_batch(config: Config, sqs_client: MagicMock) -> None:
    publisher = SqsPublisher(config, sqs_client)
    logs = [_enriched(Route.PRIORITY) for _ in range(3)]

    publisher.publish(logs)

    sqs_client.send_message_batch.assert_called_once()
    entries = sqs_client.send_message_batch.call_args.kwargs["Entries"]
    assert len(entries) == 3
    assert all("MessageGroupId" in entry for entry in entries)


def test_sqs_throttling_retries_then_raises(config: Config, sqs_client: MagicMock) -> None:
    publisher = SqsPublisher(config, sqs_client)
    error = ClientError(
        {"Error": {"Code": "ThrottlingException", "Message": "rate exceeded"}},
        "SendMessage",
    )
    sqs_client.send_message.side_effect = error

    with pytest.raises(EnqueueError):
        publisher.publish([_enriched()])

    assert sqs_client.send_message.call_count == config.sqs_max_retries


def test_batch_partial_failure_raises(config: Config, sqs_client: MagicMock) -> None:
    publisher = SqsPublisher(config, sqs_client)
    sqs_client.send_message_batch.return_value = {"Failed": [{"Id": "0", "Message": "fail"}]}

    with pytest.raises(EnqueueError):
        publisher.publish([_enriched(), _enriched()])
