from __future__ import annotations

import anthropic

from backend.config.api_keys import ApiKeyRegistry
from backend.models.escalation_policy import EscalationProviderBase


class AnthropicEscalationProvider(EscalationProviderBase):
    name = "anthropic"

    def execute(self, prompt: str, max_tokens: int, seed: int | None) -> tuple[bool, str, str]:
        _ = seed
        try:
            api_key = ApiKeyRegistry().get_api_key(self.name)
            client = anthropic.Anthropic(api_key=api_key)
            response = client.messages.create(
                model="claude-opus-4-6",
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}],
            )

            text = ""
            for block in list(getattr(response, "content", []) or []):
                block_text = getattr(block, "text", None)
                if isinstance(block_text, str) and block_text:
                    text = block_text
                    break

            return True, text, ""
        except Exception as exc:
            return False, "", str(exc)
