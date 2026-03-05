from __future__ import annotations

from typing import Any

from .base_node import BaseNode


class LLMWorkerNode(BaseNode):
    def __init__(self) -> None:
        pass

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        user_input = str(context.get("user_input", ""))
        prompt_lines: list[str] = [
            "You are the assistant in a single-turn exchange.",
            "Follow user formatting constraints exactly.",
            "Return only the assistant answer text.",
            "Do not add prefaces, explanations, or follow-up prompts unless explicitly requested.",
        ]
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
            completion_kwargs: dict[str, Any] = {
                "prompt": prompt,
                "max_tokens": 320,
                "echo": False,
                "stop": list(_STOP_SEQUENCES),
            }
            seed = context.get("generation_seed")
            if seed is not None:
                completion_kwargs["seed"] = int(seed)

            response = llm.create_completion(**completion_kwargs)

            choices = response.get("choices", []) if isinstance(response, dict) else []
            text = str(choices[0].get("text", "")) if choices else ""
            context["llm_raw_output"] = text

            context["llm_output"] = _normalize_llm_output(text)
        except Exception as exc:
            context["llm_output"] = ""
            context["llm_error"] = f"llm_generation_error: {exc}"

        return context


_LEADING_TOKENS: tuple[str, ...] = (
    "<|assistant|>",
    "<|im_start|>assistant",
    "Assistant:",
    "assistant:",
    "</s>",
    "<|end|>",
    "<|im_end|>",
)


_STOP_SEQUENCES: tuple[str, ...] = (
    "\nUser:",
    "\nAssistant:",
    "\n\nUser:",
    "\n\nAssistant:",
    "User:",
    "Assistant:",
    "<|user|>",
    "<|assistant|>",
    "<|system|>",
    "<|im_start|>user",
    "<|im_start|>assistant",
    "<|im_start|>system",
    "<|im_end|>",
    "</s>",
)


_BOUNDARY_MARKERS: tuple[str, ...] = (
    "\nUser:",
    "\nAssistant:",
    "User:",
    "Assistant:",
    "<|user|>",
    "<|assistant|>",
    "<|system|>",
    "<|im_start|>user",
    "<|im_start|>assistant",
    "<|im_start|>system",
)


_TRAILING_TOKENS: tuple[str, ...] = (
    "</s>",
    "<|end|>",
    "<|im_end|>",
)


def _normalize_llm_output(raw_text: str) -> str:
    text = str(raw_text or "").strip()

    changed = True
    while changed and text:
        changed = False
        for token in _LEADING_TOKENS:
            if text.startswith(token):
                text = text[len(token) :].lstrip()
                changed = True

    cut_positions = [text.find(marker) for marker in _BOUNDARY_MARKERS if marker in text]
    cut_positions = [position for position in cut_positions if position >= 0]
    if cut_positions:
        text = text[: min(cut_positions)]

    # If generation continues into a new paragraph after a short one-line answer,
    # keep only the first assistant segment.
    if "\n\n" in text:
        first_segment, _rest = text.split("\n\n", 1)
        if first_segment and "\n" not in first_segment and len(first_segment.split()) <= 6:
            text = first_segment

    changed = True
    while changed and text:
        changed = False
        for token in _TRAILING_TOKENS:
            if text.endswith(token):
                text = text[: -len(token)].rstrip()
                changed = True

    return text.strip()
