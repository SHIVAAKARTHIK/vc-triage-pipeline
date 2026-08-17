"""The committed HTTP cache: does a second call for the same URL actually skip
the network, and does a non-2xx response still get cached instead of raising?

Uses httpx.MockTransport so this file needs no network access — the transport
call counter is the proof that caching, not just correctness, is under test.
"""

from __future__ import annotations

import httpx
import pytest

from triage.cache import Cache, FetchError


def _counting_transport(calls: list[str], body: str = '{"ok": true}', status: int = 200):
    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(str(request.url))
        return httpx.Response(status, text=body)

    return httpx.MockTransport(handler)


def _client_with(transport: httpx.MockTransport) -> httpx.Client:
    return httpx.Client(transport=transport)


def test_first_call_hits_the_network_and_writes_a_cache_file(tmp_path) -> None:
    calls: list[str] = []
    cache = Cache(tmp_path, client=_client_with(_counting_transport(calls)))

    result = cache.get("https://example.com/a")

    assert calls == ["https://example.com/a"]
    assert result.from_cache is False
    assert result.status_code == 200
    assert list(tmp_path.glob("*.json")), "expected a cache file to be written"


def test_second_call_for_the_same_url_is_served_from_disk(tmp_path) -> None:
    calls: list[str] = []
    cache = Cache(tmp_path, client=_client_with(_counting_transport(calls)))

    first = cache.get("https://example.com/a")
    second = cache.get("https://example.com/a")

    assert calls == ["https://example.com/a"], "transport should only be hit once"
    assert second.from_cache is True
    assert second.text == first.text


def test_get_json_parses_the_cached_body(tmp_path) -> None:
    calls: list[str] = []
    transport = _counting_transport(calls, body='{"hits": [1, 2, 3]}')
    cache = Cache(tmp_path, client=_client_with(transport))

    assert cache.get_json("https://example.com/api") == {"hits": [1, 2, 3]}


def test_non_2xx_responses_are_cached_not_retried(tmp_path) -> None:
    """A 404 on an acquired company's page is a fact worth remembering, not an
    error to keep re-fetching on every run."""
    calls: list[str] = []
    transport = _counting_transport(calls, body="not found", status=404)
    cache = Cache(tmp_path, client=_client_with(transport))

    first = cache.get("https://example.com/gone")
    second = cache.get("https://example.com/gone")

    assert first.status_code == 404
    assert second.from_cache is True
    assert calls == ["https://example.com/gone"]


def test_transport_failure_raises_fetch_error_and_writes_no_cache_file(tmp_path) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    cache = Cache(tmp_path, client=_client_with(httpx.MockTransport(handler)))

    with pytest.raises(FetchError, match="connection refused"):
        cache.get("https://example.com/unreachable")

    assert not list(tmp_path.glob("*.json"))


def test_different_urls_get_different_cache_entries(tmp_path) -> None:
    calls: list[str] = []
    cache = Cache(tmp_path, client=_client_with(_counting_transport(calls)))

    cache.get("https://example.com/a")
    cache.get("https://example.com/b")

    assert len(list(tmp_path.glob("*.json"))) == 2


def test_max_body_chars_truncates_a_fresh_fetch(tmp_path) -> None:
    calls: list[str] = []
    transport = _counting_transport(calls, body="x" * 1000)
    cache = Cache(tmp_path, client=_client_with(transport))

    result = cache.get("https://example.com/big-page", max_body_chars=100)

    assert len(result.text) == 100


def test_max_body_chars_truncation_is_stable_across_a_cache_hit(tmp_path) -> None:
    """The point of truncating before writing: a replayed run sees the same
    (already-truncated) body a fresh fetch would have produced."""
    calls: list[str] = []
    transport = _counting_transport(calls, body="x" * 1000)
    cache = Cache(tmp_path, client=_client_with(transport))

    first = cache.get("https://example.com/big-page", max_body_chars=100)
    second = cache.get("https://example.com/big-page")  # no cap passed this time

    assert calls == ["https://example.com/big-page"]  # still only fetched once
    assert second.from_cache is True
    assert second.text == first.text
    assert len(second.text) == 100


def test_get_json_is_never_truncated_even_via_a_capped_get(tmp_path) -> None:
    calls: list[str] = []
    body = '{"padding": "' + ("x" * 500) + '"}'
    transport = _counting_transport(calls, body=body)
    cache = Cache(tmp_path, client=_client_with(transport))

    assert cache.get_json("https://example.com/api") == {"padding": "x" * 500}
