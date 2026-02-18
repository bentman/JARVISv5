from pathlib import Path

import pytest

from backend.models.model_registry import ModelRegistry


TEST_GPU_MODEL_PATH = "models/test-gpu.gguf"
TEST_CPU_MODEL_PATH = "models/test-cpu.gguf"


CATALOG_CONTENT = """models:
  - id: \"model-gpu-chat\"
    path: \"models/test-gpu.gguf\"
    roles: [\"chat\"]
    enabled: true
    supported_hardware: [\"gpu-cuda\", \"gpu\"]
    min_profile: \"light\"
    max_profile: \"heavy\"
    priority: 1
  - id: \"model-cpu-chat\"
    path: \"models/test-cpu.gguf\"
    roles: [\"chat\"]
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


def test_ensure_model_present_downloads_when_missing_and_enabled(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target_path = tmp_path / "models" / "downloaded.gguf"
    catalog_file = tmp_path / "models.yaml"
    catalog_file.write_text(
        """models:
  - id: "downloadable"
    path: """ + f'"{target_path.as_posix()}"' + """
    roles: ["chat"]
    enabled: true
    supported_hardware: ["cpu"]
    min_profile: "test"
    max_profile: "heavy"
    priority: 1
    download_url: "https://example.com/model.gguf"
""",
        encoding="utf-8",
    )

    registry = ModelRegistry(catalog_path=str(catalog_file))
    selected = registry.select_model(profile="medium", hardware="CPU_ONLY", role="chat")
    assert selected is not None

    calls: list[tuple[str, str]] = []

    def fake_urlretrieve(url: str, filename: str):
        calls.append((url, filename))
        Path(filename).write_bytes(b"fake-gguf")
        return filename, None

    monkeypatch.setenv("MODEL_FETCH", "missing")
    monkeypatch.setattr("backend.models.model_registry.urllib.request.urlretrieve", fake_urlretrieve)

    resolved = registry.ensure_model_present(selected)
    assert resolved == str(target_path)
    assert target_path.exists()
    assert calls and calls[0][0] == "https://example.com/model.gguf"


def test_ensure_model_present_existing_file_noop(tmp_path: Path) -> None:
    existing_path = tmp_path / "models" / "existing.gguf"
    existing_path.parent.mkdir(parents=True, exist_ok=True)
    existing_path.write_bytes(b"already-there")

    catalog_file = tmp_path / "models.yaml"
    catalog_file.write_text(
        """models:
  - id: "existing"
    path: """ + f'"{existing_path.as_posix()}"' + """
    roles: ["chat"]
    enabled: true
    supported_hardware: ["cpu"]
    min_profile: "test"
    max_profile: "heavy"
    priority: 1
""",
        encoding="utf-8",
    )

    registry = ModelRegistry(catalog_path=str(catalog_file))
    selected = registry.select_model(profile="medium", hardware="CPU_ONLY", role="chat")
    assert selected is not None

    resolved = registry.ensure_model_present(selected)
    assert resolved == str(existing_path)


def test_ensure_model_present_raises_when_missing_and_fetch_disabled(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    missing_path = tmp_path / "models" / "missing.gguf"
    catalog_file = tmp_path / "models.yaml"
    catalog_file.write_text(
        """models:
  - id: "missing"
    path: """ + f'"{missing_path.as_posix()}"' + """
    roles: ["chat"]
    enabled: true
    supported_hardware: ["cpu"]
    min_profile: "test"
    max_profile: "heavy"
    priority: 1
    download_url: "https://example.com/model.gguf"
""",
        encoding="utf-8",
    )

    registry = ModelRegistry(catalog_path=str(catalog_file))
    selected = registry.select_model(profile="medium", hardware="CPU_ONLY", role="chat")
    assert selected is not None

    monkeypatch.setenv("MODEL_FETCH", "never")
    with pytest.raises(RuntimeError, match="MODEL_FETCH=never"):
        registry.ensure_model_present(selected)
