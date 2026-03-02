from __future__ import annotations

from collections.abc import Callable
from typing import Any

from pydantic import BaseModel, Field

from backend.search.budget import SearchBudgetConfig, SearchBudgetLedger
from backend.search.extract import extract_text_from_html
from backend.search.policy import SearchPolicyRequest, decide_external_search
from backend.search.providers.ladder import ProviderLadder
from backend.tools.registry import PermissionTier, ToolDefinition, ToolRegistry
from backend.tools.sandbox import Sandbox


class SearchWebInput(BaseModel):
    query: str = Field(min_length=1)
    top_k: int = Field(default=5, ge=1)


class FetchUrlInput(BaseModel):
    url: str = Field(min_length=1)
    max_chars: int = Field(default=8000, ge=1)


def register_search_tools(registry: ToolRegistry) -> None:
    registry.register(
        ToolDefinition(
            name="search_web",
            description="Search web content via provider ladder (offline fixture-driven in tests)",
            permission_tier=PermissionTier.EXTERNAL,
            input_model=SearchWebInput,
        )
    )
    registry.register(
        ToolDefinition(
            name="fetch_url",
            description="Fetch and extract URL text content (offline fixture-driven in tests)",
            permission_tier=PermissionTier.EXTERNAL,
            input_model=FetchUrlInput,
        )
    )


def build_search_tool_dispatch_map(
    *,
    allow_external: bool,
    task_id: str | None,
    date_key: str | None,
    budget_ledger: SearchBudgetLedger | None = None,
    budget_config: SearchBudgetConfig | None = None,
    provider_ladder: ProviderLadder | None = None,
    search_payload_loader: Callable[[str, str], dict | str] | None = None,
    fetch_html_loader: Callable[[str], str] | None = None,
) -> dict[str, Any]:
    ledger = budget_ledger or SearchBudgetLedger()
    config = budget_config or SearchBudgetConfig()
    ladder = provider_ladder or ProviderLadder()

    def _policy_decision() -> tuple[bool, dict[str, object]]:
        return decide_external_search(
            SearchPolicyRequest(
                allow_external=bool(allow_external),
                estimated_cost_usd=float(config.per_call_estimate_usd),
                task_id=task_id,
                date_key=date_key,
            ),
            budget_ledger=ledger,
            config=config,
        )

    def _deny_payload(decision: dict[str, object]) -> tuple[bool, dict[str, Any]]:
        return False, {
            "code": str(decision.get("code", "permission_denied")),
            "reason": str(decision.get("reason", "external search not allowed")),
            "policy": decision,
        }

    def _run_search_web(sandbox: Sandbox, payload: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
        _ = sandbox
        if not allow_external:
            denied_decision = {
                "allow": False,
                "code": "permission_denied",
                "reason": "external search not allowed",
                "estimated_cost_usd": float(config.per_call_estimate_usd),
                "date_key": date_key or ledger.today_key(),
            }
            return _deny_payload(denied_decision)

        allowed, decision = _policy_decision()
        if not allowed:
            return _deny_payload(decision)

        request = SearchWebInput.model_validate(payload)
        search_loader = search_payload_loader
        if search_loader is None:
            ladder_result = ladder.search(
                request.query,
                request.top_k,
                payload_loader=None,
            )
        else:
            ladder_result = ladder.search(
                request.query,
                request.top_k,
                payload_loader=lambda provider_name: search_loader(provider_name, request.query),
            )

        if not ladder_result.ok or ladder_result.response is None:
            return False, {
                "code": ladder_result.code,
                "reason": ladder_result.reason,
                "policy": decision,
            }

        return True, {
            "code": "ok",
            "items": [item.model_dump() for item in ladder_result.response.items],
            "provider": ladder_result.selected_provider,
            "policy": decision,
        }

    def _run_fetch_url(sandbox: Sandbox, payload: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
        _ = sandbox
        if not allow_external:
            denied_decision = {
                "allow": False,
                "code": "permission_denied",
                "reason": "external search not allowed",
                "estimated_cost_usd": float(config.per_call_estimate_usd),
                "date_key": date_key or ledger.today_key(),
            }
            return _deny_payload(denied_decision)

        allowed, decision = _policy_decision()
        if not allowed:
            return _deny_payload(decision)

        request = FetchUrlInput.model_validate(payload)
        if fetch_html_loader is None:
            return False, {
                "code": "extraction_error",
                "reason": "html loader missing",
                "url": request.url,
                "policy": decision,
            }

        html = fetch_html_loader(request.url)
        extracted = extract_text_from_html(html, max_chars=request.max_chars)
        if not extracted.get("ok", False):
            return False, {
                "code": str(extracted.get("code", "extraction_error")),
                "reason": str(extracted.get("meta", {}).get("reason", "extraction failed")),
                "url": request.url,
                "policy": decision,
            }

        return True, {
            "code": "ok",
            "url": request.url,
            "title": extracted.get("title"),
            "text": extracted.get("text", ""),
            "policy": decision,
        }

    return {
        "search_web": _run_search_web,
        "fetch_url": _run_fetch_url,
    }
