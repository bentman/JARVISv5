import json
from pathlib import Path

from backend.search.budget import SearchBudgetConfig, SearchBudgetLedger
from backend.search.providers.base import (
    ProviderParseResult,
    ProviderRequest,
    SearchProviderBase,
    SearchResponse,
    SearchResultItem,
)
from backend.search.providers.ladder import ProviderLadder
from backend.tools.executor import ToolExecutionRequest, execute_tool_call
from backend.tools.registry import ToolRegistry
from backend.tools.sandbox import Sandbox, SandboxConfig
from backend.tools.search_tools import build_search_tool_dispatch_map, register_search_tools


SEARCH_FIXTURES = Path("tests/fixtures/search")
FETCH_FIXTURES = Path("tests/fixtures/fetch")


def _sandbox(tmp_path: Path) -> Sandbox:
    root = tmp_path / "root"
    root.mkdir()
    return Sandbox(SandboxConfig(allowed_roots=(root,)))


def test_search_web_executor_gate_denies_when_allow_external_false(tmp_path: Path) -> None:
    registry = ToolRegistry()
    register_search_tools(registry)
    sandbox = _sandbox(tmp_path)

    called = {"count": 0}

    def _loader(provider_name: str, query: str):
        _ = provider_name
        _ = query
        called["count"] += 1
        return json.loads((SEARCH_FIXTURES / "searxng_ok.json").read_text(encoding="utf-8"))

    dispatch_map = build_search_tool_dispatch_map(
        allow_external=True,
        task_id="task-1",
        date_key="2026-03-01",
        search_payload_loader=_loader,
    )

    ok, result = execute_tool_call(
        ToolExecutionRequest(
            tool_name="search_web",
            payload={"query": "python", "top_k": 3},
            allow_external=False,
        ),
        registry,
        sandbox,
        dispatch_map,
    )

    assert ok is False
    assert result["code"] == "permission_denied"
    assert result["message"] == "external permission required"
    assert called["count"] == 0


def test_search_web_policy_denies_when_budget_exceeded(tmp_path: Path) -> None:
    registry = ToolRegistry()
    register_search_tools(registry)
    sandbox = _sandbox(tmp_path)

    ledger = SearchBudgetLedger(path=tmp_path / "budget.json")
    config = SearchBudgetConfig(daily_limit_usd=1.0, per_call_estimate_usd=0.6)
    ledger.record_spend(amount_usd=0.7, date_key="2026-03-01", provider="seed")

    dispatch_map = build_search_tool_dispatch_map(
        allow_external=True,
        task_id="task-2",
        date_key="2026-03-01",
        budget_ledger=ledger,
        budget_config=config,
        search_payload_loader=lambda _p, _q: json.loads(
            (SEARCH_FIXTURES / "searxng_ok.json").read_text(encoding="utf-8")
        ),
    )

    ok, result = execute_tool_call(
        ToolExecutionRequest(
            tool_name="search_web",
            payload={"query": "python", "top_k": 2},
            allow_external=True,
        ),
        registry,
        sandbox,
        dispatch_map,
    )

    assert ok is False
    assert result["code"] == "budget_exceeded"
    assert "policy" in result
    assert result["policy"]["code"] == "budget_exceeded"


def test_search_web_allowed_returns_canonical_items_and_policy(tmp_path: Path) -> None:
    registry = ToolRegistry()
    register_search_tools(registry)
    sandbox = _sandbox(tmp_path)

    ledger = SearchBudgetLedger(path=tmp_path / "budget_ok.json")
    config = SearchBudgetConfig(daily_limit_usd=5.0, per_call_estimate_usd=0.1)

    def _loader(provider_name: str, query: str):
        _ = query
        filename = {
            "searxng": "searxng_empty.json",
            "duckduckgo": "ddg_ok.json",
            "tavily": "tavily_ok.json",
        }[provider_name]
        return json.loads((SEARCH_FIXTURES / filename).read_text(encoding="utf-8"))

    dispatch_map = build_search_tool_dispatch_map(
        allow_external=True,
        task_id="task-3",
        date_key="2026-03-01",
        budget_ledger=ledger,
        budget_config=config,
        search_payload_loader=_loader,
    )

    ok, result = execute_tool_call(
        ToolExecutionRequest(
            tool_name="search_web",
            payload={"query": "python", "top_k": 2},
            allow_external=True,
        ),
        registry,
        sandbox,
        dispatch_map,
    )

    assert ok is True
    assert result["code"] == "ok"
    assert result["provider"] == "duckduckgo"
    assert len(result["items"]) == 2
    assert result["items"][0]["source_provider"] == "duckduckgo"
    assert result["policy"]["code"] == "ok"


def test_fetch_url_allowed_returns_extracted_text_and_policy(tmp_path: Path) -> None:
    registry = ToolRegistry()
    register_search_tools(registry)
    sandbox = _sandbox(tmp_path)

    dispatch_map = build_search_tool_dispatch_map(
        allow_external=True,
        task_id="task-4",
        date_key="2026-03-01",
        budget_ledger=SearchBudgetLedger(path=tmp_path / "budget_fetch_ok.json"),
        budget_config=SearchBudgetConfig(daily_limit_usd=2.0, per_call_estimate_usd=0.1),
        fetch_html_loader=lambda _url: (FETCH_FIXTURES / "article_simple.html").read_text(encoding="utf-8"),
    )

    ok, result = execute_tool_call(
        ToolExecutionRequest(
            tool_name="fetch_url",
            payload={"url": "https://example.com/a", "max_chars": 200},
            allow_external=True,
        ),
        registry,
        sandbox,
        dispatch_map,
    )

    assert ok is True
    assert result["code"] == "ok"
    assert result["url"] == "https://example.com/a"
    assert "deterministic article body" in result["text"]
    assert result["policy"]["code"] == "ok"


def test_fetch_url_denied_by_policy_is_deterministic(tmp_path: Path) -> None:
    registry = ToolRegistry()
    register_search_tools(registry)
    sandbox = _sandbox(tmp_path)

    ledger = SearchBudgetLedger(path=tmp_path / "budget_fetch_denied.json")
    config = SearchBudgetConfig(daily_limit_usd=1.0, per_call_estimate_usd=0.8)
    ledger.record_spend(amount_usd=0.5, date_key="2026-03-01", provider="seed")

    dispatch_map = build_search_tool_dispatch_map(
        allow_external=True,
        task_id="task-5",
        date_key="2026-03-01",
        budget_ledger=ledger,
        budget_config=config,
        fetch_html_loader=lambda _url: (FETCH_FIXTURES / "article_simple.html").read_text(encoding="utf-8"),
    )

    ok, result = execute_tool_call(
        ToolExecutionRequest(
            tool_name="fetch_url",
            payload={"url": "https://example.com/a", "max_chars": 128},
            allow_external=True,
        ),
        registry,
        sandbox,
        dispatch_map,
    )

    assert ok is False
    assert result["code"] == "budget_exceeded"
    assert result["policy"]["code"] == "budget_exceeded"


def test_search_web_preferred_provider_failure_is_deterministic_without_fallback(tmp_path: Path) -> None:
    registry = ToolRegistry()
    register_search_tools(registry)
    sandbox = _sandbox(tmp_path)

    class _FailingTavilyProvider(SearchProviderBase):
        name = "tavily"

        def parse_response(self, payload: dict | str, request: ProviderRequest) -> ProviderParseResult:
            _ = payload
            _ = request
            return ProviderParseResult(ok=False, code="unauthorized", reason="unauthorized")

        def execute_request(self, request: ProviderRequest) -> ProviderParseResult:
            _ = request
            return ProviderParseResult(ok=False, code="unauthorized", reason="unauthorized")

    class _SuccessfulSearxngProvider(SearchProviderBase):
        name = "searxng"

        def parse_response(self, payload: dict | str, request: ProviderRequest) -> ProviderParseResult:
            _ = payload
            _ = request
            return ProviderParseResult(ok=False, code="provider_unavailable", reason="not_used")

        def execute_request(self, request: ProviderRequest) -> ProviderParseResult:
            _ = request
            return ProviderParseResult(
                ok=True,
                code="ok",
                reason="ok",
                response=SearchResponse(
                    items=[
                        SearchResultItem(
                            title="SearXNG success",
                            url="https://example.com/searxng",
                            snippet="fallback should not be used",
                            source_provider=self.name,
                        )
                    ],
                    provider=self.name,
                    raw_cost_usd=0.0,
                    warnings=[],
                ),
            )

    class _SuccessfulDdgProvider(SearchProviderBase):
        name = "duckduckgo"

        def parse_response(self, payload: dict | str, request: ProviderRequest) -> ProviderParseResult:
            _ = payload
            _ = request
            return ProviderParseResult(ok=False, code="provider_unavailable", reason="not_used")

        def execute_request(self, request: ProviderRequest) -> ProviderParseResult:
            _ = request
            return ProviderParseResult(
                ok=True,
                code="ok",
                reason="ok",
                response=SearchResponse(
                    items=[
                        SearchResultItem(
                            title="DDG success",
                            url="https://example.com/ddg",
                            snippet="fallback should not be used",
                            source_provider=self.name,
                        )
                    ],
                    provider=self.name,
                    raw_cost_usd=0.0,
                    warnings=[],
                ),
            )

    custom_ladder = ProviderLadder(
        providers=[
            _SuccessfulSearxngProvider(),
            _SuccessfulDdgProvider(),
            _FailingTavilyProvider(),
        ]
    )

    dispatch_map = build_search_tool_dispatch_map(
        allow_external=True,
        task_id="task-preferred-failure",
        date_key="2026-03-02",
        budget_ledger=SearchBudgetLedger(path=tmp_path / "budget_preferred_failure.json"),
        budget_config=SearchBudgetConfig(daily_limit_usd=2.0, per_call_estimate_usd=0.1),
        provider_ladder=custom_ladder,
    )

    ok, result = execute_tool_call(
        ToolExecutionRequest(
            tool_name="search_web",
            payload={"query": "python", "top_k": 3, "preferred_provider": "tavily"},
            allow_external=True,
        ),
        registry,
        sandbox,
        dispatch_map,
    )

    assert ok is False
    assert result["code"] == "provider_unavailable"
    assert result["reason"] == "unauthorized"
    assert result["preferred_provider"] == "tavily"
    assert "provider" not in result
    assert "items" not in result
