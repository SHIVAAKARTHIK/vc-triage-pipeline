"""The committed HTTP cache — see Fig. 1 in the project overview and ADR 0001.

Every response the source stage receives is written to `data/raw/<sha256(url)>.json`
and committed, so a reviewer re-running the pipeline hits the cache, not the
network: same evidence, same candidates, no API keys required to reproduce a run.

Deliberately caches non-2xx responses too (a 404 on an acquired company's YC page
is itself a fact worth remembering) and only raises `FetchError` for genuine
transport failures — timeouts, DNS, connection refused — which the source stage
is expected to catch per-candidate so one bad fetch doesn't sink an entire run.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

DEFAULT_USER_AGENT = "triage-pipeline/0.1 (case-study; contact: karthikshiva.manju65@gmail.com)"
DEFAULT_TIMEOUT = 20.0


class FetchError(RuntimeError):
    """A URL could not be fetched and was not already cached."""


@dataclass
class CachedResponse:
    url: str
    status_code: int
    text: str
    fetched_at: datetime
    from_cache: bool


class Cache:
    """A disk-backed HTTP cache. Use as a context manager to own its own client:

        with Cache(Path("data/raw")) as cache:
            body = cache.get_json("https://example.com/api")

    Or inject an `httpx.Client` (e.g. one built on `httpx.MockTransport`) for tests.
    """

    def __init__(
        self,
        root: Path,
        client: httpx.Client | None = None,
        user_agent: str = DEFAULT_USER_AGENT,
    ) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        self._client = client or httpx.Client(
            timeout=DEFAULT_TIMEOUT, headers={"User-Agent": user_agent}, follow_redirects=True
        )
        self._owns_client = client is None

    def _path_for(self, url: str) -> Path:
        digest = hashlib.sha256(url.encode("utf-8")).hexdigest()
        return self.root / f"{digest}.json"

    def get(self, url: str, max_body_chars: int | None = None) -> CachedResponse:
        """Fetch (or replay) a URL. `max_body_chars` truncates the *cached and
        returned* body — used for HTML pages we only ever read the head of (see
        source.py), never for JSON, where a truncated body wouldn't parse.
        Truncation happens before writing to disk, so a cache hit replays the
        same (already-truncated) text a fresh fetch would have produced.
        """
        path = self._path_for(url)
        if path.exists():
            record = json.loads(path.read_text(encoding="utf-8"))
            return CachedResponse(
                url=record["url"],
                status_code=record["status_code"],
                text=record["text"],
                fetched_at=datetime.fromisoformat(record["fetched_at"]),
                from_cache=True,
            )

        try:
            response = self._client.get(url)
        except httpx.HTTPError as exc:
            raise FetchError(f"GET {url} failed: {exc}") from exc

        text = response.text
        if max_body_chars is not None and len(text) > max_body_chars:
            text = text[:max_body_chars]

        fetched_at = datetime.now(UTC)
        record = {
            "url": url,
            "status_code": response.status_code,
            "text": text,
            "fetched_at": fetched_at.isoformat(),
        }
        path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
        return CachedResponse(
            url=url, status_code=response.status_code, text=text,
            fetched_at=fetched_at, from_cache=False,
        )

    def get_json(self, url: str) -> Any:
        """Never truncated — a partial JSON document wouldn't parse."""
        return json.loads(self.get(url).text)

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def __enter__(self) -> Cache:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()
