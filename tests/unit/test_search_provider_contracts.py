import json
from pathlib import Path

from backend.search.providers.ddg import DuckDuckGoProvider
from backend.search.providers.searxng import SearXNGProvider
from backend.search.providers.tavily import TavilyProvider


FIXTURE_DIR = Path("tests/fixtures/search")


def _load_fixture(name: str) -> dict:
    return json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))


def test_searxng_parse_ok_fixture_to_canonical_shape() -> None:
    provider = SearXNGProvider()
    request = provider.build_request("q", top_k=2)

    parsed = provider.parse_response(_load_fixture("searxng_ok.json"), request)

    assert parsed.ok is True
    assert parsed.code == "ok"
    assert parsed.response is not None
    assert parsed.response.provider == "searxng"
    assert len(parsed.response.items) == 2
    assert parsed.response.items[0].title == "SearXNG Result One"
    assert parsed.response.items[0].url == "https://example.com/searxng/1"
    assert parsed.response.items[0].snippet == "Snippet from searxng one"
    assert parsed.response.items[0].source_provider == "searxng"


def test_ddg_parse_ok_fixture_to_canonical_shape() -> None:
    provider = DuckDuckGoProvider()
    request = provider.build_request("q", top_k=2)

    parsed = provider.parse_response(_load_fixture("ddg_ok.json"), request)

    assert parsed.ok is True
    assert parsed.code == "ok"
    assert parsed.response is not None
    assert parsed.response.provider == "duckduckgo"
    assert len(parsed.response.items) == 2
    assert parsed.response.items[0].title == "DDG Result One"
    assert parsed.response.items[0].url == "https://example.com/ddg/1"
    assert parsed.response.items[0].snippet == "Snippet from ddg one"
    assert parsed.response.items[0].source_provider == "duckduckgo"


def test_tavily_parse_ok_fixture_to_canonical_shape() -> None:
    provider = TavilyProvider()
    request = provider.build_request("q", top_k=1)

    parsed = provider.parse_response(_load_fixture("tavily_ok.json"), request)

    assert parsed.ok is True
    assert parsed.code == "ok"
    assert parsed.response is not None
    assert parsed.response.provider == "tavily"
    assert len(parsed.response.items) == 1
    assert parsed.response.items[0].title == "Tavily Result One"
    assert parsed.response.items[0].url == "https://example.com/tavily/1"
    assert parsed.response.items[0].snippet == "Snippet from tavily one"
    assert parsed.response.items[0].source_provider == "tavily"


def test_provider_malformed_payload_fails_deterministically_without_exception() -> None:
    payload = _load_fixture("malformed.json")

    for provider in (SearXNGProvider(), DuckDuckGoProvider(), TavilyProvider()):
        request = provider.build_request("q", top_k=3)
        parsed = provider.parse_response(payload, request)
        assert parsed.ok is False
        assert parsed.code == "validation_error"
        assert parsed.reason == "missing results"


def test_provider_empty_payload_fails_deterministically() -> None:
    provider = SearXNGProvider()
    request = provider.build_request("q", top_k=3)

    parsed = provider.parse_response(_load_fixture("searxng_empty.json"), request)

    assert parsed.ok is False
    assert parsed.code == "empty_results"
    assert parsed.reason == "no results"


def test_provider_tier_metadata_classification() -> None:
    searxng = SearXNGProvider()
    ddg = DuckDuckGoProvider()
    tavily = TavilyProvider()

    assert searxng.is_external is False
    assert searxng.is_paid is False

    assert ddg.is_external is True
    assert ddg.is_paid is False

    assert tavily.is_external is True
    assert tavily.is_paid is True
