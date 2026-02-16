from __future__ import annotations

from typing import Any

from .base_node import BaseNode


class LLMWorkerNode(BaseNode):
    def __init__(self, model_path: str = "models/tinyllama-1.1b-chat.gguf") -> None:
        self.model_path = model_path

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        prompt = str(context.get("user_input", ""))
        context["llm_model_path"] = self.model_path

        try:
            from llama_cpp import Llama

            context["llm_imported"] = True
        except Exception as exc:  # pragma: no cover - depends on runtime image
            context["llm_imported"] = False
            context["llm_output"] = ""
            context["llm_error"] = f"llama_cpp_import_error: {exc}"
            return context

        try:
            llm = Llama(model_path=self.model_path, n_ctx=2048, verbose=False)
            response = llm.create_completion(prompt=prompt, max_tokens=100, echo=False)

            choices = response.get("choices", []) if isinstance(response, dict) else []
            text = choices[0].get("text", "") if choices else ""
            context["llm_output"] = str(text)
        except Exception as exc:
            context["llm_output"] = ""
            context["llm_error"] = f"llm_generation_error: {exc}"

        return context
