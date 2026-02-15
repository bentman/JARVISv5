from pathlib import Path

from backend.models.model_registry import ModelRegistry


CATALOG_CONTENT = """models:
  - id: \"llama-3-8b-instruct\"
    filename: \"models/llama-3-8b-instruct.gguf\"
    role: \"general\"
    hardware_type: \"GPU_CUDA\"
    min_vram_gb: 6
  - id: \"tinyllama-chat\"
    filename: \"models/tinyllama-1.1b-chat.gguf\"
    role: \"chat\"
    hardware_type: \"CPU_ONLY\"
    min_vram_gb: 1
"""


def test_registry_loads_models(tmp_path: Path) -> None:
    catalog_file = tmp_path / "models.yaml"
    catalog_file.write_text(CATALOG_CONTENT, encoding="utf-8")

    registry = ModelRegistry(catalog_path=str(catalog_file))
    assert len(registry.models) == 2


def test_select_model_for_gpu_general_role(tmp_path: Path) -> None:
    catalog_file = tmp_path / "models.yaml"
    catalog_file.write_text(CATALOG_CONTENT, encoding="utf-8")

    registry = ModelRegistry(catalog_path=str(catalog_file))
    selected = registry.select_model("GPU_CUDA", "general")
    assert selected == "models/llama-3-8b-instruct.gguf"
