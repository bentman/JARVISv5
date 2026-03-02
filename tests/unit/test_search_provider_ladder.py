import json
from pathlib import Path

import backend.search.providers.ddg as ddg_module
from backend.search.providers.base import (
    ProviderParseResult,
    ProviderRequest,
    SearchProviderBase,
    SearchResponse,
    SearchResultItem,
)
from backend.search.providers.ddg import DuckDuckGoProvider
from backend.search.providers.ladder import ProviderLadder


FIXTURE_DIR = Path("tests/fixtures/search")


def _payload_loader_from_map(mapping: dict[str, str]):
    def _loader(provider_name: str):
        fixture_name = mapping[provider_name]
        return json.loads((FIXTURE_DIR / fixture_name).read_text(encoding="utf-8"))

    return _loader


def test_ladder_falls_back_from_searxng_empty_to_ddg_ok() -> None:
    ladder = ProviderLadder()
    loader = _payload_loader_from_map(
        {
            "searxng": "searxng_empty.json",
            "duckduckgo": "ddg_ok.json",
            "tavily": "tavily_ok.json",
        }
    )

    result = ladder.search("python", top_k=2, payload_loader=loader)

    assert result.ok is True
    assert result.code == "ok"
    assert result.selected_provider == "duckduckgo"
    assert result.attempted_providers == ["searxng", "duckduckgo"]
    assert result.response is not None
    assert len(result.response.items) == 2


def test_ladder_falls_through_to_tavily_when_first_two_fail() -> None:
    ladder = ProviderLadder()
    loader = _payload_loader_from_map(
        {
            "searxng": "malformed.json",
            "duckduckgo": "searxng_empty.json",
            "tavily": "tavily_ok.json",
        }
    )

    result = ladder.search("python", top_k=2, payload_loader=loader)

    assert result.ok is True
    assert result.code == "ok"
    assert result.selected_provider == "tavily"
    assert result.attempted_providers == ["searxng", "duckduckgo", "tavily"]
    assert result.response is not None
    assert len(result.response.items) == 1


def test_ladder_returns_provider_unavailable_when_all_fail() -> None:
    ladder = ProviderLadder()
    loader = _payload_loader_from_map(
        {
            "searxng": "searxng_empty.json",
            "duckduckgo": "malformed.json",
            "tavily": "searxng_empty.json",
        }
    )

    result = ladder.search("python", top_k=2, payload_loader=loader)

    assert result.ok is False
    assert result.code == "provider_unavailable"
    assert result.reason == "no provider returned results"
    assert result.selected_provider is None
    assert result.attempted_providers == ["searxng", "duckduckgo", "tavily"]


def test_ladder_without_payload_loader_uses_provider_execute_request_path() -> None:
    class _LiveStubProvider(SearchProviderBase):
        name = "searxng"

        def parse_response(self, payload: dict | str, request: ProviderRequest) -> ProviderParseResult:
            _ = payload
            _ = request
            return ProviderParseResult(ok=False, code="provider_unavailable", reason="not_used")

        def execute_request(self, request: ProviderRequest) -> ProviderParseResult:
            return ProviderParseResult(
                ok=True,
                code="ok",
                reason="ok",
                response=SearchResponse(
                    items=[
                        SearchResultItem(
                            title=f"Live result for {request.query}",
                            url="https://example.com/live",
                            snippet="stub",
                            source_provider=self.name,
                        )
                    ],
                    provider=self.name,
                    raw_cost_usd=0.0,
                    warnings=[],
                ),
            )

    ladder = ProviderLadder(providers=[_LiveStubProvider()])
    result = ladder.search("python", top_k=1, payload_loader=None)

    assert result.ok is True
    assert result.code == "ok"
    assert result.selected_provider == "searxng"
    assert result.attempted_providers == ["searxng"]
    assert result.response is not None
    assert len(result.response.items) == 1
    assert result.response.items[0].title == "Live result for python"


def test_ladder_without_payload_loader_uses_ddg_execute_request_with_monkeypatched_ddgs(monkeypatch) -> None:
    class _FakeDDGS:
        def text(self, query: str, max_results: int = 5, **kwargs):
            _ = kwargs
            assert query == "python"
            assert max_results == 2
            return [
                {
                    "title": "Python Official",
                    "href": "https://www.python.org/",
                    "body": "Welcome to Python.org",
                },
                {
                    "title": "Missing href row",
                    "body": "should be filtered before parse",
                },
            ]

    monkeypatch.setattr(ddg_module, "DDGS", _FakeDDGS)

    ladder = ProviderLadder(providers=[DuckDuckGoProvider()])
    result = ladder.search("python", top_k=2, payload_loader=None)

    assert result.ok is True
    assert result.code == "ok"
    assert result.selected_provider == "duckduckgo"
    assert result.attempted_providers == ["duckduckgo"]
    assert result.response is not None
    assert len(result.response.items) >= 1
    assert result.response.items[0].url == "https://www.python.org/"
