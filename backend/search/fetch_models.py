from __future__ import annotations

from pydantic import BaseModel, Field


class ExtractionResult(BaseModel):
    ok: bool
    code: str
    text: str
    title: str | None = None
    meta: dict = Field(default_factory=dict)
