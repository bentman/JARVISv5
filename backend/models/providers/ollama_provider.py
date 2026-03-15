from __future__ import annotations

import httpx

from backend.config.settings import Settings
from backend.models.escalation_policy import EscalationProviderBase


class OllamaEscalationProvider(EscalationProviderBase):
    name = "ollama"

    def execute(self, prompt: str, max_tokens: int, seed: int | None) -> tuple[bool, str, str]:
        _ = seed
        settings = Settings()
        base_url = str(getattr(settings, "OLLAMA_BASE_URL", "") or "").strip()
        model = str(getattr(settings, "OLLAMA_MODEL", "") or "").strip()

        if not model:
            return False, "", "ollama_model_not_configured"

        url = f"{base_url.rstrip('/')}/api/generate"
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {"num_predict": max_tokens},
        }

        try:
            response = httpx.post(url, json=payload, timeout=30.0)
        except httpx.RequestError:
            return False, "", "ollama_unreachable"

        if response.status_code != 200:
            return False, "", f"ollama_http_status_{response.status_code}"

        try:
            body = response.json()
        except Exception:
            return False, "", "ollama_malformed_response"

        text = body.get("response") if isinstance(body, dict) else None
        if not isinstance(text, str) or not text.strip():
            return False, "", "ollama_malformed_response"

        return True, text, ""
