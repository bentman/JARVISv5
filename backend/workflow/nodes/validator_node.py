from __future__ import annotations

from typing import Any

from .base_node import BaseNode


_MODEL_ERROR_MARKERS = (
    "local model missing",
    "llm_model_path_missing",
    "llama_cpp_import_error",
)


class ValidatorNode(BaseNode):
    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        output = str(context.get("llm_output", "")).strip()
        output_lower = output.lower()
        validation_errors: list[str] = []

        if output == "":
            validation_errors.append("empty_output")

        if output != "" and len(output) < 8:
            validation_errors.append("too_short")

        if any(marker in output_lower for marker in _MODEL_ERROR_MARKERS):
            validation_errors.append("model_error_output")

        llm_error = str(context.get("llm_error", "")).strip()
        if llm_error:
            validation_errors.append("explicit_llm_error")

        context["validation_errors"] = validation_errors
        context["validation_status"] = "passed" if not validation_errors else "failed"
        context["is_valid"] = not validation_errors
        return context
