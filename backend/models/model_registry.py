from pathlib import Path
from typing import Any

import yaml


class ModelRegistry:
    def __init__(self, catalog_path: str = "data/models.yaml") -> None:
        self.catalog_path = Path(catalog_path)
        self.models: list[dict[str, Any]] = []
        self._load_catalog()

    def _load_catalog(self) -> None:
        if not self.catalog_path.exists():
            self.models = []
            return

        content = yaml.safe_load(self.catalog_path.read_text(encoding="utf-8")) or {}
        loaded_models = content.get("models", [])
        if not isinstance(loaded_models, list):
            self.models = []
            return
        self.models = [model for model in loaded_models if isinstance(model, dict)]

    def _is_hardware_compatible(self, requested: str, candidate: str) -> bool:
        if requested == candidate:
            return True

        compatibility_map: dict[str, set[str]] = {
            "GPU_CUDA": {"GPU_GENERAL", "CPU_ONLY"},
            "GPU_GENERAL": {"CPU_ONLY"},
            "NPU_APPLE": {"GPU_GENERAL", "CPU_ONLY"},
            "NPU_INTEL": {"GPU_GENERAL", "CPU_ONLY"},
        }
        return candidate in compatibility_map.get(requested, set())

    def select_model(self, hardware_type: str, role: str) -> str | None:
        compatible_models = [
            model
            for model in self.models
            if self._is_hardware_compatible(hardware_type, str(model.get("hardware_type", "")))
        ]

        role_models = [model for model in compatible_models if str(model.get("role", "")) == role]
        if not role_models:
            return None

        filename = role_models[0].get("filename")
        return str(filename) if filename else None
