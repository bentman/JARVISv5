import json
import os
import shutil


class WorkingStateManager:
    def __init__(
        self,
        base_path: str = "data/working_state",
        archive_path: str = "data/archives",
    ) -> None:
        self.base_path = base_path
        self.archive_path = archive_path
        os.makedirs(self.base_path, exist_ok=True)
        os.makedirs(self.archive_path, exist_ok=True)

    def _sanitize_task_id(self, task_id: str) -> str:
        normalized = task_id.replace("\\", "/")
        base = os.path.basename(normalized)
        safe = "".join(ch for ch in base if ch.isalnum() or ch in ("-", "_"))
        if not safe:
            raise ValueError("Invalid task_id")
        return safe

    def _working_file_path(self, task_id: str) -> str:
        safe_task_id = self._sanitize_task_id(task_id)
        return os.path.join(self.base_path, f"{safe_task_id}.json")

    def _archive_file_path(self, task_id: str) -> str:
        safe_task_id = self._sanitize_task_id(task_id)
        return os.path.join(self.archive_path, f"{safe_task_id}.json")

    def create_task(self, task_id: str, goal: str, initial_steps: list[str]) -> dict:
        task = {
            "task_id": self._sanitize_task_id(task_id),
            "goal": goal,
            "status": "INIT",
            "current_step": 1,
            "total_steps": len(initial_steps),
            "completed_steps": [1],
            "next_steps": initial_steps,
        }
        with open(self._working_file_path(task_id), "w", encoding="utf-8") as handle:
            json.dump(task, handle, indent=2)
        return task

    def get_task(self, task_id: str) -> dict | None:
        file_path = self._working_file_path(task_id)
        if not os.path.exists(file_path):
            return None
        with open(file_path, "r", encoding="utf-8") as handle:
            return json.load(handle)

    def update_status(self, task_id: str, new_status: str) -> dict:
        task = self.get_task(task_id)
        if task is None:
            raise FileNotFoundError("Task not found")

        task["status"] = new_status
        with open(self._working_file_path(task_id), "w", encoding="utf-8") as handle:
            json.dump(task, handle, indent=2)
        return task

    def increment_step(self, task_id: str) -> dict:
        task = self.get_task(task_id)
        if task is None:
            raise FileNotFoundError("Task not found")

        task["current_step"] = int(task["current_step"]) + 1
        completed_steps = list(task.get("completed_steps", []))
        if task["current_step"] not in completed_steps:
            completed_steps.append(task["current_step"])
        task["completed_steps"] = completed_steps

        with open(self._working_file_path(task_id), "w", encoding="utf-8") as handle:
            json.dump(task, handle, indent=2)
        return task

    def archive_task(self, task_id: str) -> dict:
        task = self.get_task(task_id)
        if task is None:
            raise FileNotFoundError("Task not found")

        task["status"] = "ARCHIVED"
        working_file = self._working_file_path(task_id)
        archive_file = self._archive_file_path(task_id)

        with open(working_file, "w", encoding="utf-8") as handle:
            json.dump(task, handle, indent=2)

        shutil.move(working_file, archive_file)
        return task
