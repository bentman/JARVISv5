from __future__ import annotations

import importlib
from typing import Any

from backend.config.settings import Settings
from backend.search.providers.base import (
    ProviderParseResult,
    ProviderRequest,
    SearchProviderBase,
    SearchResponse,
    SearchResultItem,
)


class TavilyProvider(SearchProviderBase):
    name = "tavily"
    is_external = True
    is_paid = True

    def __init__(self, api_key: str | None = None) -> None:
        self._api_key = api_key

    def execute_request(self, request: ProviderRequest) -> ProviderParseResult:
        api_key = (self._api_key or "").strip()
        if not api_key:
            init_kwargs: dict[str, Any] = {"_env_file": None}
            api_key = str(Settings(**init_kwargs).TAVILY_API_KEY).strip()
        if not api_key:
            return ProviderParseResult(ok=False, code="provider_unavailable", reason="unauthorized")

        try:
            tavily_module = importlib.import_module("tavily")
            client_cls = getattr(tavily_module, "TavilyClient", None)
        except Exception:
            client_cls = None

        if client_cls is None:
            return ProviderParseResult(ok=False, code="provider_unavailable", reason="request_error")

        try:
            payload_raw = client_cls(api_key=api_key).search(
                request.query,
                max_results=request.top_k,
            )
        except Exception as exc:
            code, reason = self._map_live_exception(exc)
            return ProviderParseResult(ok=False, code=code, reason=reason)

        results_raw = payload_raw.get("results") if isinstance(payload_raw, dict) else []
        normalized_results: list[dict[str, object]] = []
        if isinstance(results_raw, list):
            for row in results_raw:
                if not isinstance(row, dict):
                    continue
                normalized_results.append(
                    {
                        "title": row.get("title", ""),
                        "url": row.get("url", ""),
                        "content": row.get("content"),
                    }
                )

        return self.parse_response({"results": normalized_results}, request)

    @staticmethod
    def _map_live_exception(exc: Exception) -> tuple[str, str]:
        name = exc.__class__.__name__.lower()
        message = str(exc).lower()
        status_code = getattr(exc, "status_code", None)
        if status_code is None:
            response_obj = getattr(exc, "response", None)
            status_code = getattr(response_obj, "status_code", None)

        if status_code == 401 or "401" in message or "unauthorized" in message or "invalid api key" in message:
            return "provider_unavailable", "unauthorized"
        if status_code == 429 or "429" in message or "rate limit" in message or "ratelimit" in name or "too many requests" in message:
            return "provider_unavailable", "ratelimit"
        if "timeout" in name or "timeout" in message:
            return "provider_unavailable", "timeout"
        return "provider_unavailable", "request_error"

    def parse_response(self, payload: dict | str, request: ProviderRequest) -> ProviderParseResult:
        ok, data, reason = self._load_payload_dict(payload)
        if not ok:
            return ProviderParseResult(ok=False, code="parse_error", reason=reason)

        results = data.get("results")
        if results is None:
            return ProviderParseResult(ok=False, code="validation_error", reason="missing results")
        if not isinstance(results, list):
            return ProviderParseResult(ok=False, code="validation_error", reason="results must be list")

        items: list[SearchResultItem] = []
        for row in results:
            if not isinstance(row, dict):
                continue
            title = str(row.get("title", "")).strip()
            url = str(row.get("url", "")).strip()
            snippet_raw = row.get("content")
            snippet = None if snippet_raw is None else str(snippet_raw)
            if not title or not url:
                continue
            items.append(
                SearchResultItem(
                    title=title,
                    url=url,
                    snippet=snippet,
                    source_provider=self.name,
                )
            )

        items = items[: request.top_k]
        if not items:
            return ProviderParseResult(
                ok=False,
                code="empty_results",
                reason="no results",
                response=SearchResponse(items=[], provider=self.name, raw_cost_usd=0.0, warnings=[]),
            )

        return ProviderParseResult(
            ok=True,
            code="ok",
            reason="ok",
            response=SearchResponse(items=items, provider=self.name, raw_cost_usd=0.0, warnings=[]),
        )
