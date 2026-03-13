from __future__ import annotations

import openai

from backend.config.api_keys import ApiKeyRegistry
from backend.models.escalation_policy import EscalationProviderBase


class OpenAIEscalationProvider(EscalationProviderBase):
    name = "openai"

    def execute(self, prompt: str, max_tokens: int, seed: int | None) -> tuple[bool, str, str]:
        try:
            api_key = ApiKeyRegistry().get_api_key(self.name)
            client = openai.OpenAI(api_key=api_key)
            response = client.chat.completions.create(
                model="gpt-4o",
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}],
                seed=seed,
            )

            text = ""
            if getattr(response, "choices", None):
                message = response.choices[0].message
                content = getattr(message, "content", "")
                text = str(content or "")

            return True, text, ""
        except Exception as exc:
            return False, "", str(exc)
