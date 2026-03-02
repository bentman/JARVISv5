from __future__ import annotations

import json
from abc import ABC, abstractmethod

from pydantic import BaseModel, Field


class SearchResultItem(BaseModel):
    title: str
    url: str
    snippet: str | None = None
    source_provider: str


class SearchResponse(BaseModel):
    items: list[SearchResultItem] = Field(default_factory=list)
    provider: str
    raw_cost_usd: float | None = None
    warnings: list[str] = Field(default_factory=list)


class ProviderRequest(BaseModel):
    query: str
    top_k: int = Field(ge=1)


class ProviderParseResult(BaseModel):
    ok: bool
    code: str
    reason: str
    response: SearchResponse | None = None


class LadderSearchResult(BaseModel):
    ok: bool
    code: str
    reason: str
    response: SearchResponse | None = None
    selected_provider: str | None = None
    attempted_providers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class SearchProviderBase(ABC):
    name: str

    def build_request(self, query: str, *, top_k: int) -> ProviderRequest:
        return ProviderRequest(query=query, top_k=top_k)

    @abstractmethod
    def parse_response(self, payload: dict | str, request: ProviderRequest) -> ProviderParseResult:
        raise NotImplementedError

    def _load_payload_dict(self, payload: dict | str) -> tuple[bool, dict, str]:
        if isinstance(payload, dict):
            return True, payload, ""
        if isinstance(payload, str):
            try:
                parsed = json.loads(payload)
            except json.JSONDecodeError:
                return False, {}, "invalid json payload"
            if isinstance(parsed, dict):
                return True, parsed, ""
            return False, {}, "payload must decode to object"
        return False, {}, "payload must be dict or json string"
