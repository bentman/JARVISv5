import json
import tempfile
from pathlib import Path

from backend.memory.working_state import WorkingStateManager


def test_create_task_creates_file_with_expected_content() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        base_path = Path(tmp_dir) / "working"
        archive_path = Path(tmp_dir) / "archive"
        manager = WorkingStateManager(str(base_path), str(archive_path))

        created = manager.create_task(
            task_id="../uuid-1234",
            goal="User request string",
            initial_steps=["Step A", "Step B"],
        )

        file_path = base_path / "uuid-1234.json"
        assert file_path.exists()

        content = json.loads(file_path.read_text(encoding="utf-8"))
        assert content["task_id"] == "uuid-1234"
        assert content["status"] == "INIT"
        assert content["total_steps"] == 2
        assert created["task_id"] == "uuid-1234"


def test_get_task_returns_task_data() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        manager = WorkingStateManager(
            str(Path(tmp_dir) / "working"),
            str(Path(tmp_dir) / "archive"),
        )
        manager.create_task("task-1", "goal", ["next"])

        task = manager.get_task("task-1")
        assert task is not None
        assert task["task_id"] == "task-1"


def test_update_status_persists_change() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        manager = WorkingStateManager(
            str(Path(tmp_dir) / "working"),
            str(Path(tmp_dir) / "archive"),
        )
        manager.create_task("task-2", "goal", ["next"])

        manager.update_status("task-2", "PLANNING")
        task = manager.get_task("task-2")
        assert task is not None
        assert task["status"] == "PLANNING"


def test_increment_step_updates_counters() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        manager = WorkingStateManager(
            str(Path(tmp_dir) / "working"),
            str(Path(tmp_dir) / "archive"),
        )
        manager.create_task("task-3", "goal", ["a", "b", "c"])

        updated = manager.increment_step("task-3")
        assert updated["current_step"] == 2
        assert 2 in updated["completed_steps"]


def test_archive_task_moves_file_to_archive() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        base_path = Path(tmp_dir) / "working"
        archive_path = Path(tmp_dir) / "archive"
        manager = WorkingStateManager(str(base_path), str(archive_path))
        manager.create_task("task-4", "goal", ["a"])

        archived = manager.archive_task("task-4")
        assert archived["status"] == "ARCHIVED"
        assert not (base_path / "task-4.json").exists()
        assert (archive_path / "task-4.json").exists()
