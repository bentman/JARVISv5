import tempfile
from pathlib import Path

from backend.controller.controller_service import ControllerService
from backend.memory.memory_manager import MemoryManager
from backend.models.hardware_profiler import HardwareService, HardwareType
from backend.models.model_registry import ModelRegistry


class TestEmbeddingFunction:
    def encode(self, text: str) -> list[float]:
        base = float((sum(ord(ch) for ch in text) % 13) + 1)
        return [base] * 384


def build_memory(tmp_dir: str) -> MemoryManager:
    base = Path(tmp_dir)
    return MemoryManager(
        episodic_db_path=str(base / "episodic.db"),
        working_base_path=str(base / "working"),
        working_archive_path=str(base / "archives"),
        semantic_db_path=str(base / "semantic.db"),
        embedding_model=TestEmbeddingFunction(),
    )


class StubHardwareService(HardwareService):
    def detect_hardware_type(self) -> HardwareType:
        return HardwareType.CPU_ONLY

    def get_hardware_profile(self) -> str:
        return "light"


class StubModelRegistry(ModelRegistry):
    def __init__(self) -> None:
        self.models = []

    def select_model(self, profile: str, hardware: str, role: str) -> dict | None:
        return None


def test_controller_persists_workflow_graph_and_execution_order_to_task_state() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        service = ControllerService(
            memory_manager=build_memory(tmp_dir),
            hardware_service=StubHardwareService(),
            model_registry=StubModelRegistry(),
        )

        result = service.run(user_input="persist workflow telemetry")
        task_state = service.memory.get_task_state(result["task_id"])

        assert isinstance(task_state, dict)
        assert isinstance(task_state.get("workflow_graph"), dict)
        assert "workflow_execution_order" in task_state
        assert isinstance(task_state["workflow_execution_order"], list)
        assert len(task_state["workflow_execution_order"]) > 0
        assert all(isinstance(node_id, str) for node_id in task_state["workflow_execution_order"])
