import json
from pathlib import Path

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
