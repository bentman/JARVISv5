from __future__ import annotations

from typing import Any

from .base_node import BaseNode


class LLMWorkerNode(BaseNode):
    def __init__(self) -> None:
        pass

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        prompt = str(context.get("user_input", ""))
        selected_model = context.get("selected_model", {})
        model_path = str(
            context.get("llm_model_path")
            or (selected_model.get("path") if isinstance(selected_model, dict) else "")
            or ""
        )
        context["llm_model_path"] = model_path

        if not model_path:
            context["llm_output"] = ""
            context["llm_error"] = "llm_model_path_missing"
            return context

        try:
            from llama_cpp import Llama

            context["llm_imported"] = True
        except Exception as exc:  # pragma: no cover - depends on runtime image
            context["llm_imported"] = False
            context["llm_output"] = ""
            context["llm_error"] = f"llama_cpp_import_error: {exc}"
            return context

        try:
            llm = Llama(model_path=model_path, n_ctx=2048, verbose=False)
            response = llm.create_completion(prompt=prompt, max_tokens=100, echo=False)

            choices = response.get("choices", []) if isinstance(response, dict) else []
            text = choices[0].get("text", "") if choices else ""
            context["llm_output"] = str(text)
        except Exception as exc:
            context["llm_output"] = ""
            context["llm_error"] = f"llm_generation_error: {exc}"

        return context
