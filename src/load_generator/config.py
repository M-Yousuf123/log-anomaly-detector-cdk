from __future__ import annotations

import os
from pathlib import Path

INGEST_API_URL_ENV = "INGEST_API_URL"


def load_dotenv(path: Path | None = None) -> None:
    env_path = path or Path(".env")
    if not env_path.is_file():
        return

    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def resolve_api_url(cli_override: str | None = None) -> str:
    if cli_override:
        return cli_override.rstrip("/")

    url = os.environ.get(INGEST_API_URL_ENV, "").strip()
    if not url:
        raise RuntimeError(
            f"Set {INGEST_API_URL_ENV} in .env or pass --api-url."
        )
    return url.rstrip("/")
