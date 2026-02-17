from pathlib import Path

from backend.models.model_registry import ModelRegistry


TEST_GPU_MODEL_PATH = "models/test-gpu.gguf"
TEST_CPU_MODEL_PATH = "models/test-cpu.gguf"


CATALOG_CONTENT = """models:
  - id: \"model-gpu-chat\"
    path: \"models/test-gpu.gguf\"
    role: \"chat\"
    enabled: true
    supported_hardware: [\"gpu-cuda\", \"gpu\"]
    min_profile: \"light\"
    max_profile: \"heavy\"
    priority: 1
  - id: \"model-cpu-chat\"
    path: \"models/test-cpu.gguf\"
    role: \"chat\"
    enabled: true
    supported_hardware: [\"cpu\"]
    min_profile: \"test\"
    max_profile: \"heavy\"
    priority: 2
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
    selected = registry.select_model(profile="medium", hardware="GPU_CUDA", role="chat")
    assert selected is not None
    assert selected["path"] == TEST_GPU_MODEL_PATH


def test_select_model_falls_back_to_cpu(tmp_path: Path) -> None:
    catalog_file = tmp_path / "models.yaml"
    catalog_file.write_text(CATALOG_CONTENT, encoding="utf-8")

    registry = ModelRegistry(catalog_path=str(catalog_file))
    selected = registry.select_model(profile="light", hardware="CPU_ONLY", role="chat")
    assert selected is not None
    assert selected["path"] == TEST_CPU_MODEL_PATH
