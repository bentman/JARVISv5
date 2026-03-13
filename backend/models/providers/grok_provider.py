from __future__ import annotations

import openai

from backend.config.api_keys import ApiKeyRegistry
from backend.models.escalation_policy import EscalationProviderBase


class GrokEscalationProvider(EscalationProviderBase):
    name = "grok"

    def execute(self, prompt: str, max_tokens: int, seed: int | None) -> tuple[bool, str, str]:
        _ = seed
        try:
            api_key = ApiKeyRegistry().get_api_key(self.name)
            client = openai.OpenAI(
                api_key=api_key,
                base_url="https://api.x.ai/v1",
            )
            response = client.chat.completions.create(
                model="grok-3",
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}],
            )

            text = ""
            if getattr(response, "choices", None):
                message = response.choices[0].message
                content = getattr(message, "content", "")
                text = str(content or "")

            return True, text, ""
        except Exception as exc:
            return False, "", str(exc)
