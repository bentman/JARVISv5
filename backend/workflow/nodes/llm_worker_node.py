from __future__ import annotations

import re
from typing import Any

from .base_node import BaseNode


class LLMWorkerNode(BaseNode):
    def __init__(self) -> None:
        pass

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        user_input = str(context.get("user_input", ""))
        raw_messages = context.get("messages", [])
        messages: list[dict[str, str]] = []
        if isinstance(raw_messages, list):
            for item in raw_messages[-10:]:
                if isinstance(item, dict):
                    role = str(item.get("role", "user")).strip().lower()
                    content = str(item.get("content", "")).strip()
                    if content:
                        messages.append({"role": role, "content": content})

        if messages:
            prompt_lines: list[str] = [
                "Instruction: Answer the user's question directly and concisely."
            ]
            for item in messages:
                role = item["role"]
                if role == "user":
                    prompt_lines.append(f"User: {item['content']}")
            prompt_lines.append("Assistant:")
            prompt = "\n".join(prompt_lines)
        else:
            prompt = user_input

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
                max_tokens=100,
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
            first_line = first_turn.splitlines()[0] if first_turn.splitlines() else first_turn
            normalized = first_line.strip()

            name_match = re.search(r"\bname\s+is\s+([A-Za-z][A-Za-z'-]*)\b", normalized, flags=re.IGNORECASE)
            if name_match:
                normalized = name_match.group(1)

            context["llm_output"] = normalized
        except Exception as exc:
            context["llm_output"] = ""
            context["llm_error"] = f"llm_generation_error: {exc}"

        return context
