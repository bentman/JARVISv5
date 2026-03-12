from __future__ import annotations

from typing import Any

import backend.workflow.nodes.search_web_node as search_web_node_module
from backend.workflow.nodes.search_web_node import SearchWebNode


def _searxng_ok() -> dict[str, Any]:
    return {
        "results": [
            {
                "title": "SearXNG Result",
                "url": "https://example.com/searxng",
                "content": "searxng snippet",
            }
        ]
    }


def _ddg_ok() -> dict[str, Any]:
    return {
        "results": [
            {
                "title": "DDG Result",
                "href": "https://example.com/ddg",
                "body": "ddg snippet",
            }
        ]
    }


def _tavily_ok() -> dict[str, Any]:
    return {
        "results": [
            {
                "title": "Tavily Result",
                "url": "https://example.com/tavily",
                "content": "tavily snippet",
            }
        ]
    }


class _UnlimitedBudgetLedger:
    def today_key(self) -> str:
        return "2026-03-12"

    def remaining_budget_usd(self, date_key: str, daily_limit_usd: float) -> float:
        _ = date_key, daily_limit_usd
        return 999.0

    def can_spend(self, amount_usd: float, date_key: str, daily_limit_usd: float) -> bool:
        _ = amount_usd, date_key, daily_limit_usd
        return True


def _patch_budget_ledger(monkeypatch) -> None:
    monkeypatch.setattr(search_web_node_module, "SearchBudgetLedger", _UnlimitedBudgetLedger)


def test_search_web_node_searxng_only_mode(monkeypatch) -> None:
    class _Settings:
        ALLOW_EXTERNAL_SEARCH = False
        ALLOW_PAID_SEARCH = False
        TAVILY_API_KEY = ""
        DEFAULT_SEARCH_PROVIDER = "duckduckgo"
        SEARCH_SEARXNG_URL = "http://searxng:8080/search"

    monkeypatch.setattr(search_web_node_module, "Settings", lambda: _Settings)
    _patch_budget_ledger(monkeypatch)

    node = SearchWebNode()
    context = {
        "search_query": "python",
        "search_payload_loader": lambda provider: _searxng_ok(),
    }

    result = node.execute(context)
    assert result["search_ok"] is True
    assert result["search_provider"] == "searxng"
    assert len(result["search_results"]) == 1
    assert result["search_error"] is None


def test_search_web_node_searxng_plus_ddg_mode(monkeypatch) -> None:
    class _Settings:
        ALLOW_EXTERNAL_SEARCH = True
        ALLOW_PAID_SEARCH = False
        TAVILY_API_KEY = ""
        DEFAULT_SEARCH_PROVIDER = "duckduckgo"
        SEARCH_SEARXNG_URL = "http://searxng:8080/search"

    monkeypatch.setattr(search_web_node_module, "Settings", lambda: _Settings)
    _patch_budget_ledger(monkeypatch)

    node = SearchWebNode()
    context = {
        "search_query": "python",
        "search_payload_loader": lambda provider: _ddg_ok() if provider == "duckduckgo" else _searxng_ok(),
    }

    result = node.execute(context)
    assert result["search_ok"] is True
    assert result["search_provider"] == "duckduckgo"
    assert len(result["search_results"]) == 1
    assert result["search_error"] is None


def test_search_web_node_all_three_provider_mode_prefers_default(monkeypatch) -> None:
    class _Settings:
        ALLOW_EXTERNAL_SEARCH = True
        ALLOW_PAID_SEARCH = True
        TAVILY_API_KEY = "test-key"
        DEFAULT_SEARCH_PROVIDER = "tavily"
        SEARCH_SEARXNG_URL = "http://searxng:8080/search"

    monkeypatch.setattr(search_web_node_module, "Settings", lambda: _Settings)
    _patch_budget_ledger(monkeypatch)

    node = SearchWebNode()
    context = {
        "search_query": "python",
        "search_payload_loader": lambda provider: _tavily_ok() if provider == "tavily" else _ddg_ok(),
    }

    result = node.execute(context)
    assert result["search_ok"] is True
    assert result["search_provider"] == "tavily"
    assert len(result["search_results"]) == 1
    assert result["search_error"] is None


def test_search_web_node_all_fail_sets_search_ok_false(monkeypatch) -> None:
    class _Settings:
        ALLOW_EXTERNAL_SEARCH = True
        ALLOW_PAID_SEARCH = True
        TAVILY_API_KEY = "test-key"
        DEFAULT_SEARCH_PROVIDER = "tavily"
        SEARCH_SEARXNG_URL = "http://searxng:8080/search"

    monkeypatch.setattr(search_web_node_module, "Settings", lambda: _Settings)
    _patch_budget_ledger(monkeypatch)

    node = SearchWebNode()
    context = {
        "search_query": "python",
        "search_payload_loader": lambda provider: {"malformed": True},
    }

    result = node.execute(context)
    assert result["search_ok"] is False
    assert result["search_provider"] is None
    assert result["search_results"] == []
    assert isinstance(result["search_error"], str)


def test_search_web_node_policy_denied_sets_blocked_context(monkeypatch) -> None:
    class _Settings:
        ALLOW_EXTERNAL_SEARCH = False
        ALLOW_PAID_SEARCH = False
        TAVILY_API_KEY = ""
        DEFAULT_SEARCH_PROVIDER = "duckduckgo"
        SEARCH_SEARXNG_URL = "http://searxng:8080/search"

    monkeypatch.setattr(search_web_node_module, "Settings", lambda: _Settings)

    def _deny_policy(*args, **kwargs):
        _ = args, kwargs
        return False, {"reason": "external search not allowed"}

    monkeypatch.setattr(search_web_node_module, "decide_external_search", _deny_policy)

    node = SearchWebNode()
    context = {
        "search_query": "python",
        "search_payload_loader": lambda provider: _searxng_ok(),
    }

    result = node.execute(context)
    assert result["search_ok"] is False
    assert result["search_provider"] is None
    assert result["search_results"] == []
    assert result["search_error"] == "external search not allowed"


def test_search_web_node_same_input_same_output(monkeypatch) -> None:
    class _Settings:
        ALLOW_EXTERNAL_SEARCH = True
        ALLOW_PAID_SEARCH = False
        TAVILY_API_KEY = ""
        DEFAULT_SEARCH_PROVIDER = "duckduckgo"
        SEARCH_SEARXNG_URL = "http://searxng:8080/search"

    monkeypatch.setattr(search_web_node_module, "Settings", lambda: _Settings)
    _patch_budget_ledger(monkeypatch)

    node = SearchWebNode()
    context_a = {
        "search_query": "python",
        "search_payload_loader": lambda provider: _ddg_ok() if provider == "duckduckgo" else _searxng_ok(),
    }
    context_b = {
        "search_query": "python",
        "search_payload_loader": lambda provider: _ddg_ok() if provider == "duckduckgo" else _searxng_ok(),
    }

    result_a = node.execute(dict(context_a))
    result_b = node.execute(dict(context_b))

    assert result_a["search_ok"] is True
    assert result_b["search_ok"] is True
    assert result_a["search_provider"] == result_b["search_provider"]
    assert result_a["search_results"] == result_b["search_results"]
    assert result_a["search_error"] == result_b["search_error"]
