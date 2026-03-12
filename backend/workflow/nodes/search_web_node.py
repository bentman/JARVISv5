from __future__ import annotations

from collections.abc import Callable
from typing import Any

from backend.config.settings import Settings
from backend.search.budget import SearchBudgetConfig, SearchBudgetLedger
from backend.search.policy import SearchPolicyRequest, decide_external_search
from backend.search.providers.ddg import DuckDuckGoProvider
from backend.search.providers.ladder import ProviderLadder
from backend.search.providers.searxng import SearXNGProvider
from backend.search.providers.tavily import TavilyProvider
from backend.workflow.nodes.base_node import BaseNode


class SearchWebNode(BaseNode):
    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        query_raw = context.get("search_query", context.get("user_input", ""))
        query = str(query_raw).strip()
        if not query:
            context["search_results"] = []
            context["search_provider"] = None
            context["search_ok"] = False
            context["search_error"] = "query missing"
            return context

        settings = Settings()
        allow_external_search = bool(settings.ALLOW_EXTERNAL_SEARCH)
        allow_paid_search = bool(settings.ALLOW_PAID_SEARCH)
        tavily_key = str(settings.TAVILY_API_KEY).strip()
        paid_key_configured = bool(tavily_key)
        preferred_provider = str(settings.DEFAULT_SEARCH_PROVIDER).strip().lower() or None

        providers = [
            SearXNGProvider(base_url=str(settings.SEARCH_SEARXNG_URL)),
        ]
        if allow_external_search:
            providers.append(DuckDuckGoProvider())
            if allow_paid_search and paid_key_configured:
                providers.append(TavilyProvider(api_key=tavily_key))

        policy_provider = next(
            (provider for provider in providers if provider.name == preferred_provider),
            providers[0],
        )

        date_key_raw = context.get("search_date_key")
        date_key = str(date_key_raw).strip() if date_key_raw is not None else None
        if not date_key:
            date_key = None

        estimated_cost_raw = context.get("search_estimated_cost_usd")
        estimated_cost: float | None = None
        if estimated_cost_raw is not None:
            try:
                estimated_cost = float(estimated_cost_raw)
            except (TypeError, ValueError):
                estimated_cost = None

        policy_request = SearchPolicyRequest(
            allow_external=allow_external_search,
            estimated_cost_usd=estimated_cost,
            date_key=date_key,
            task_id=str(context.get("task_id")) if context.get("task_id") is not None else None,
            provider_is_external=bool(policy_provider.is_external),
            provider_is_paid=bool(policy_provider.is_paid),
            allow_paid_search=allow_paid_search,
            paid_key_configured=paid_key_configured,
        )
        allowed, policy_result = decide_external_search(
            request=policy_request,
            budget_ledger=SearchBudgetLedger(),
            config=SearchBudgetConfig(),
        )
        if not allowed:
            context["search_results"] = []
            context["search_provider"] = None
            context["search_ok"] = False
            context["search_error"] = str(policy_result.get("reason", "search blocked"))
            return context

        top_k_raw = context.get("search_top_k", 5)
        try:
            top_k = max(1, int(top_k_raw))
        except (TypeError, ValueError):
            top_k = 5

        payload_loader_raw = context.get("search_payload_loader")
        payload_loader = (
            payload_loader_raw
            if callable(payload_loader_raw)
            else None
        )
        typed_payload_loader = (
            payload_loader
            if payload_loader is None
            else (lambda provider_name: payload_loader(provider_name))
        )

        ladder = ProviderLadder(providers=providers)
        ladder_result = ladder.search(
            query=query,
            top_k=top_k,
            payload_loader=typed_payload_loader,
            preferred_provider=preferred_provider,
        )

        if not ladder_result.ok or ladder_result.response is None:
            context["search_results"] = []
            context["search_provider"] = None
            context["search_ok"] = False
            context["search_error"] = str(ladder_result.reason)
            return context

        context["search_results"] = [item.model_dump() for item in ladder_result.response.items]
        context["search_provider"] = str(ladder_result.selected_provider)
        context["search_ok"] = True
        context["search_error"] = None
        return context
