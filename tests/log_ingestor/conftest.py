"""Pytest configuration — bootstrap env vars and shared fixtures."""

from __future__ import annotations

import os
from unittest.mock import MagicMock

import pytest

from log_ingestor.config import Config, load_config
from log_ingestor.enricher import DefaultLogEnricher
from log_ingestor.router import DefaultLogRouter
from log_ingestor.validator import DefaultLogValidator

from factories import TEST_MAIN_QUEUE_URL, TEST_PRIORITY_QUEUE_URL, TEST_REGION

os.environ.setdefault("AWS_DEFAULT_REGION", TEST_REGION)
os.environ.setdefault("MAIN_QUEUE_URL", TEST_MAIN_QUEUE_URL)
os.environ.setdefault("PRIORITY_QUEUE_URL", TEST_PRIORITY_QUEUE_URL)


@pytest.fixture
def config() -> Config:
    return load_config()


@pytest.fixture
def sqs_client() -> MagicMock:
    return MagicMock()


@pytest.fixture
def validator() -> DefaultLogValidator:
    return DefaultLogValidator()


@pytest.fixture
def router() -> DefaultLogRouter:
    return DefaultLogRouter()


@pytest.fixture
def enricher() -> DefaultLogEnricher:
    return DefaultLogEnricher()
