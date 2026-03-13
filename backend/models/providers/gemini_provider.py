from __future__ import annotations

from importlib import import_module

from backend.config.api_keys import ApiKeyRegistry
from backend.models.escalation_policy import EscalationProviderBase


def _get_genai_module():
    return import_module("google.genai")


class GeminiEscalationProvider(EscalationProviderBase):
    name = "gemini"

    def execute(self, prompt: str, max_tokens: int, seed: int | None) -> tuple[bool, str, str]:
        _ = max_tokens
        _ = seed
        try:
            genai = _get_genai_module()
            api_key = ApiKeyRegistry().get_api_key(self.name)
            client = genai.Client(api_key=api_key)
            response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt,
            )
            text = str(getattr(response, "text", "") or "")
            return True, text, ""
        except Exception as exc:
            return False, "", str(exc)
