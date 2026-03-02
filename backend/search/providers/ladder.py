from __future__ import annotations

from collections.abc import Callable

from backend.search.providers.base import LadderSearchResult, SearchProviderBase
from backend.search.providers.ddg import DuckDuckGoProvider
from backend.search.providers.searxng import SearXNGProvider
from backend.search.providers.tavily import TavilyProvider


class ProviderLadder:
    def __init__(self, providers: list[SearchProviderBase] | None = None) -> None:
        self.providers = providers or [SearXNGProvider(), DuckDuckGoProvider(), TavilyProvider()]

    def search(
        self,
        query: str,
        top_k: int,
        payload_loader: Callable[[str], dict | str] | None = None,
    ) -> LadderSearchResult:
        attempted: list[str] = []
        warnings: list[str] = []

        if payload_loader is None:
            return LadderSearchResult(
                ok=False,
                code="provider_unavailable",
                reason="no provider returned results",
                selected_provider=None,
                attempted_providers=[],
                warnings=["payload loader required"],
            )

        for provider in self.providers:
            attempted.append(provider.name)
            request = provider.build_request(query, top_k=top_k)
            payload = payload_loader(provider.name)
            parsed = provider.parse_response(payload, request)
            if parsed.ok and parsed.response is not None and len(parsed.response.items) > 0:
                return LadderSearchResult(
                    ok=True,
                    code="ok",
                    reason="ok",
                    response=parsed.response,
                    selected_provider=provider.name,
                    attempted_providers=attempted,
                    warnings=warnings,
                )
            warnings.append(f"{provider.name}:{parsed.code}")

        return LadderSearchResult(
            ok=False,
            code="provider_unavailable",
            reason="no provider returned results",
            selected_provider=None,
            attempted_providers=attempted,
            warnings=warnings,
        )
