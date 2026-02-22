from __future__ import annotations

from typing import Any

from .base_node import BaseNode


class LLMWorkerNode(BaseNode):
    def __init__(self) -> None:
        pass

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        user_input = str(context.get("user_input", ""))
        prompt_lines: list[str] = ["Answer the user's latest message directly and concisely."]
        prompt_lines.append(f"User: {user_input}")
        prompt_lines.append("Assistant:")
        prompt = "\n".join(prompt_lines)

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
            response = llm.create_completion(
                prompt=prompt,
                max_tokens=320,
                echo=False,
                stop=["\nUser:", "\nAssistant:", "User:", "Assistant:"],
            )

            choices = response.get("choices", []) if isinstance(response, dict) else []
            text = str(choices[0].get("text", "")) if choices else ""
            context["llm_raw_output"] = text

            first_turn = text
            for marker in ("\nUser:", "\nAssistant:", "User:", "Assistant:"):
                if marker in first_turn:
                    first_turn = first_turn.split(marker, 1)[0]
            context["llm_output"] = first_turn.strip()
        except Exception as exc:
            context["llm_output"] = ""
            context["llm_error"] = f"llm_generation_error: {exc}"

        return context
