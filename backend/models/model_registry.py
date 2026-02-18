from pathlib import Path
from typing import Any

import yaml


class ModelRegistry:
    def __init__(self, catalog_path: str = "models/models.yaml") -> None:
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

    def _normalize_profile(self, profile: str) -> str:
        normalized = profile.strip().lower().replace("_", "-")
        mapping = {
            "heavy": "heavy",
            "medium": "medium",
            "light": "light",
            "test": "test",
            "npu-optimized": "npu-optimized",
        }
        return mapping.get(normalized, normalized)

    def _normalize_hardware(self, hardware: str) -> str:
        normalized = hardware.strip().upper().replace("-", "_")
        mapping = {
            "GPU_CUDA": "gpu-cuda",
            "GPU_GENERAL": "gpu",
            "NPU_APPLE": "npu",
            "NPU_INTEL": "npu",
            "QUALCOMM_NPU": "npu",
            "CPU_ONLY": "cpu",
            "GPU": "gpu",
            "NPU": "npu",
            "CPU": "cpu",
        }
        return mapping.get(normalized, hardware.strip().lower())

    def _profile_rank(self, profile: str) -> int:
        order = {
            "test": 0,
            "light": 1,
            "medium": 2,
            "heavy": 3,
            "npu-optimized": 4,
        }
        return order.get(self._normalize_profile(profile), 0)

    def _allowed_hardware(self, requested: str) -> list[str]:
        fallback = {
            "gpu-cuda": ["gpu-cuda", "gpu", "cpu"],
            "gpu": ["gpu", "cpu"],
            "npu": ["npu", "gpu", "cpu"],
            "cpu": ["cpu"],
        }
        return fallback.get(requested, [requested, "cpu"])

    def _coerce_model_path(self, model: dict[str, Any]) -> str:
        path = model.get("path")
        if isinstance(path, str) and path:
            return path
        filename = model.get("filename")
        if isinstance(filename, str) and filename:
            return filename
        return ""

    def select_model(self, profile: str, hardware: str, role: str) -> dict[str, Any] | None:
        normalized_profile = self._normalize_profile(profile)
        normalized_hardware = self._normalize_hardware(hardware)
        allowed_hardware = set(self._allowed_hardware(normalized_hardware))

        enabled_models = [
            model
            for model in self.models
            if bool(model.get("enabled", True))
        ]
        role_models: list[dict[str, Any]] = []
        for model in enabled_models:
            roles = model.get("roles")
            if isinstance(roles, list):
                if role in {str(item) for item in roles}:
                    role_models.append(model)
                continue

            legacy_role = str(model.get("role", ""))
            if legacy_role == role:
                role_models.append(model)

        hardware_models = []
        for model in role_models:
            supported = model.get("supported_hardware")
            if isinstance(supported, list):
                normalized_supported = {
                    self._normalize_hardware(str(item)) for item in supported
                }
            else:
                legacy = str(model.get("hardware_type", ""))
                normalized_supported = {self._normalize_hardware(legacy)} if legacy else set()

            if normalized_supported & allowed_hardware:
                hardware_models.append(model)

        profile_rank = self._profile_rank(normalized_profile)
        profile_models = []
        for model in hardware_models:
            min_profile = self._normalize_profile(str(model.get("min_profile", "test")))
            max_profile = self._normalize_profile(
                str(model.get("max_profile", "npu-optimized"))
            )
            if self._profile_rank(min_profile) <= profile_rank <= self._profile_rank(max_profile):
                profile_models.append(model)

        sorted_models = sorted(
            profile_models,
            key=lambda model: (
                int(model.get("priority", 100)),
                str(model.get("id", "")),
            ),
        )
        if not sorted_models:
            return None

        selected = dict(sorted_models[0])
        selected["path"] = self._coerce_model_path(selected)
        selected["normalized_profile"] = normalized_profile
        selected["normalized_hardware"] = normalized_hardware
        return selected
