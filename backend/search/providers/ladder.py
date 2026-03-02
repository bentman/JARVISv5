from __future__ import annotations

from collections.abc import Callable

from backend.search.providers.base import LadderSearchResult, SearchProviderBase
from backend.search.providers.ddg import DuckDuckGoProvider
from backend.search.providers.searxng import SearXNGProvider
from backend.search.providers.tavily import TavilyProvider


DEFAULT_PROVIDER_CLASSES: tuple[type[SearchProviderBase], ...] = (
    SearXNGProvider,
    DuckDuckGoProvider,
    TavilyProvider,
)
DEFAULT_PROVIDER_NAMES: tuple[str, ...] = tuple(provider_cls.name for provider_cls in DEFAULT_PROVIDER_CLASSES)


class ProviderLadder:
    def __init__(self, providers: list[SearchProviderBase] | None = None) -> None:
        self.providers = providers or [provider_cls() for provider_cls in DEFAULT_PROVIDER_CLASSES]

    @staticmethod
    def default_provider_names() -> tuple[str, ...]:
        return DEFAULT_PROVIDER_NAMES

    def search(
        self,
        query: str,
        top_k: int,
        payload_loader: Callable[[str], dict | str] | None = None,
        preferred_provider: str | None = None,
    ) -> LadderSearchResult:
        attempted: list[str] = []
        warnings: list[str] = []
        providers = self.providers

        if preferred_provider:
            preferred = preferred_provider.strip().lower()
            providers = sorted(
                self.providers,
                key=lambda provider: 0 if provider.name == preferred else 1,
            )

        for provider in providers:
            attempted.append(provider.name)
            request = provider.build_request(query, top_k=top_k)
            if payload_loader is None:
                parsed = provider.execute_request(request)
            else:
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
