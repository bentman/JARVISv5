from __future__ import annotations

from backend.search.providers.base import (
    ProviderParseResult,
    ProviderRequest,
    SearchProviderBase,
    SearchResponse,
    SearchResultItem,
)


class SearXNGProvider(SearchProviderBase):
    name = "searxng"

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
