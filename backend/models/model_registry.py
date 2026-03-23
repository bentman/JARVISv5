import os
from pathlib import Path
from typing import Any
import urllib.request

import yaml


# Non-functional alignment touch: hwalignspec closure marker.

def normalize_hardware_type(hardware: str) -> str:
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

    def _coerce_model_dir(self, model: dict[str, Any]) -> str:
        model_dir = model.get("model_dir")
        if isinstance(model_dir, str) and model_dir:
            return model_dir
        return ""

    def _coerce_model_target(self, model: dict[str, Any]) -> tuple[str, str]:
        model_dir = self._coerce_model_dir(model)
        if model_dir:
            return "dir", model_dir
        model_path = self._coerce_model_path(model)
        if model_path:
            return "file", model_path
        return "", ""

    def ensure_model_present_hf(self, model_id: str, target_dir: Path) -> None:
        try:
            from huggingface_hub import snapshot_download
        except Exception as exc:
            raise RuntimeError(
                "Directory model fetch requires huggingface_hub; install dependency before enabling MODEL_FETCH=missing for model_dir entries"
            ) from exc

        snapshot_download(repo_id=model_id, local_dir=str(target_dir))

    def ensure_model_present(self, model: dict[str, Any]) -> str:
        target_type, model_target = self._coerce_model_target(model)
        if not model_target:
            raise RuntimeError("Selected model does not define a usable path or model_dir")

        path = Path(model_target)
        if target_type == "dir":
            if path.exists() and path.is_dir():
                print(f"[model-fetch] using existing model directory: {path}")
                return str(path)
        elif path.exists():
            print(f"[model-fetch] using existing model: {path}")
            return str(path)

        fetch_mode = os.getenv("MODEL_FETCH", "never").strip().lower()
        if fetch_mode != "missing":
            if target_type == "dir":
                raise RuntimeError(
                    f"Model directory missing and MODEL_FETCH={fetch_mode}: {path}"
                )
            raise RuntimeError(f"Model file missing and MODEL_FETCH={fetch_mode}: {path}")

        if target_type == "dir":
            model_id = model.get("model_id")
            if not isinstance(model_id, str) or not model_id.strip():
                raise RuntimeError(
                    f"Model directory missing and model_id is not set: {path}"
                )

            path.parent.mkdir(parents=True, exist_ok=True)
            try:
                print(
                    f"[model-fetch] downloading missing model directory: {model_id} -> {path}"
                )
                self.ensure_model_present_hf(model_id.strip(), path)
                if not path.exists() or not path.is_dir():
                    raise RuntimeError(
                        f"Model directory download did not produce a directory: {path}"
                    )
                print(f"[model-fetch] directory download complete: {path}")
            except Exception as exc:
                raise RuntimeError(
                    f"Model directory download failed for {path}: {exc}"
                ) from exc

            return str(path)

        download_url = model.get("download_url")
        if not isinstance(download_url, str) or not download_url.strip():
            raise RuntimeError(f"Model file missing and download_url is not set: {path}")

        path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = Path(f"{path}.tmp")
        try:
            print(f"[model-fetch] downloading missing model: {download_url} -> {path}")
            urllib.request.urlretrieve(download_url, str(tmp_path))
            os.replace(tmp_path, path)
            print(f"[model-fetch] download complete: {path}")
        except Exception as exc:
            try:
                if tmp_path.exists():
                    tmp_path.unlink()
            except Exception:
                pass
            raise RuntimeError(f"Model download failed for {path}: {exc}") from exc

        return str(path)

    def select_model(self, profile: str, hardware: str, role: str) -> dict[str, Any] | None:
        normalized_profile = self._normalize_profile(profile)
        normalized_hardware = normalize_hardware_type(hardware)
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
                    normalize_hardware_type(str(item)) for item in supported
                }
            else:
                legacy = str(model.get("hardware_type", ""))
                normalized_supported = {normalize_hardware_type(legacy)} if legacy else set()

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
        _, selected_target = self._coerce_model_target(selected)
        selected["path"] = selected_target
        selected["normalized_profile"] = normalized_profile
        selected["normalized_hardware"] = normalized_hardware
        return selected
