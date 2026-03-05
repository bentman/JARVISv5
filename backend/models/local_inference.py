from __future__ import annotations

from typing import Any


class LocalInferenceClient:
    def __init__(self, model_path: str) -> None:
        self.model_path = model_path
        self.model: Any | None = None

    def load_model(self) -> None:
        import llama_cpp

        self.model = llama_cpp.Llama(
            model_path=self.model_path,
            n_ctx=2048,
            verbose=False,
        )

    def generate(self, prompt: str, max_tokens: int = 100, seed: int | None = None) -> str:
        if self.model is None:
            raise RuntimeError("Model is not loaded. Call load_model() before generate().")

        completion_kwargs: dict[str, Any] = {
            "max_tokens": max_tokens,
            "echo": False,
        }
        if seed is not None:
            completion_kwargs["seed"] = int(seed)

        response = self.model.create_completion(prompt, **completion_kwargs)

        choices = response.get("choices", []) if isinstance(response, dict) else []
        if not choices:
            return ""

        text = choices[0].get("text", "")
        return str(text)
