from __future__ import annotations

import os

import httpx

from backend.search.providers.base import (
    ProviderParseResult,
    ProviderRequest,
    SearchProviderBase,
    SearchResponse,
    SearchResultItem,
)


class SearXNGProvider(SearchProviderBase):
    name = "searxng"

    def execute_request(self, request: ProviderRequest) -> ProviderParseResult:
        base_url = os.getenv("SEARCH_SEARXNG_URL", "http://searxng:8080/search")
        try:
            with httpx.Client(timeout=httpx.Timeout(5.0, connect=2.0)) as client:
                response = client.get(
                    base_url,
                    params={"q": request.query, "format": "json"},
                )
        except httpx.ConnectError:
            return ProviderParseResult(ok=False, code="provider_unavailable", reason="connect_error")
        except httpx.TimeoutException:
            return ProviderParseResult(ok=False, code="provider_unavailable", reason="timeout")
        except Exception:
            return ProviderParseResult(ok=False, code="provider_unavailable", reason="live_request_failed")

        if response.status_code != 200:
            return ProviderParseResult(
                ok=False,
                code="provider_unavailable",
                reason=f"http_status_{response.status_code}",
            )

        try:
            payload = response.json()
        except ValueError:
            return ProviderParseResult(ok=False, code="parse_error", reason="invalid_json")

        return self.parse_response(payload, request)

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
