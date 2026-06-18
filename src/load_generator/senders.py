from __future__ import annotations

import argparse
import json
import ssl
import urllib.error
import urllib.request
from typing import Any

import boto3
import certifi
from botocore.exceptions import BotoCoreError, ClientError

from load_generator.config import resolve_api_url
from load_generator.models import LogSender, Transport


def _ssl_context() -> ssl.SSLContext:
    return ssl.create_default_context(cafile=certifi.where())


class HttpLogSender:
    def __init__(self, api_url: str, timeout_s: float) -> None:
        self._url = f"{api_url}/logs"
        self._timeout_s = timeout_s
        self._ssl_context = _ssl_context()

    def send_batch(
        self, logs: list[dict[str, Any]], correlation_id: str
    ) -> tuple[int, int, str | None]:
        payload = json.dumps({"logs": logs}).encode()
        request = urllib.request.Request(
            self._url,
            data=payload,
            headers={
                "Content-Type": "application/json",
                "x-correlation-id": correlation_id,
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(
                request, timeout=self._timeout_s, context=self._ssl_context
            ) as response:
                body = json.loads(response.read().decode())
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode(errors="replace")
            return 0, len(logs), f"HTTP {exc.code}: {detail}"
        except urllib.error.URLError as exc:
            return 0, len(logs), f"Request failed: {exc.reason}"

        return int(body.get("accepted", 0)), int(body.get("rejected", 0)), None


class LambdaLogSender:
    def __init__(self, function_name: str, region: str) -> None:
        self._client = boto3.client("lambda", region_name=region)
        self._function_name = function_name

    def send_batch(
        self, logs: list[dict[str, Any]], correlation_id: str
    ) -> tuple[int, int, str | None]:
        event = {
            "requestContext": {"requestId": correlation_id},
            "headers": {"x-correlation-id": correlation_id},
            "body": json.dumps({"logs": logs}),
        }
        try:
            response = self._client.invoke(
                FunctionName=self._function_name,
                InvocationType="RequestResponse",
                Payload=json.dumps(event).encode(),
            )
        except (BotoCoreError, ClientError) as exc:
            return 0, len(logs), f"Lambda invoke failed: {exc}"

        if response.get("FunctionError"):
            payload = response.get("Payload")
            detail = payload.read().decode() if payload else "unknown lambda error"
            return 0, len(logs), detail

        payload = json.loads(response["Payload"].read().decode())
        api_body = json.loads(payload.get("body", "{}"))
        return int(api_body.get("accepted", 0)), int(api_body.get("rejected", 0)), None


def build_sender(args: argparse.Namespace) -> LogSender:
    if args.transport == Transport.LAMBDA:
        return LambdaLogSender(function_name=args.lambda_name, region=args.region)

    return HttpLogSender(api_url=resolve_api_url(args.api_url), timeout_s=args.timeout)
