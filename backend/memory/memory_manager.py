from typing import Any

from .episodic_db import EpisodicMemory
from .semantic_store import SemanticMemory
from .working_state import WorkingStateManager


class MemoryManager:
    def __init__(
        self,
        episodic_db_path: str = "data/episodic/trace.db",
        working_base_path: str = "data/working_state",
        working_archive_path: str = "data/archives",
        semantic_db_path: str = "data/semantic/metadata.db",
        embedding_model: Any = None,
    ) -> None:
        self.episodic = EpisodicMemory(db_path=episodic_db_path)
        self.working = WorkingStateManager(
            base_path=working_base_path,
            archive_path=working_archive_path,
        )
        self.semantic = SemanticMemory(
            db_path=semantic_db_path,
            embedding_model=embedding_model,
        )

    def log_decision(self, task_id: str, action_type: str, content: str, status: str) -> int:
        return self.episodic.log_decision(task_id, action_type, content, status)

    def log_tool_call(self, decision_id: int, tool_name: str, params: str, result: str) -> int:
        return self.episodic.log_tool_call(decision_id, tool_name, params, result)

    def create_task(self, task_id: str, goal: str, steps: list[str]) -> dict:
        return self.working.create_task(task_id, goal, steps)

    def get_task_state(self, task_id: str) -> dict | None:
        return self.working.get_task(task_id)

    def update_task_status(self, task_id: str, status: str) -> dict:
        return self.working.update_status(task_id, status)

    def archive_task(self, task_id: str) -> dict:
        return self.working.archive_task(task_id)

    def store_knowledge(self, text: str, metadata: dict[str, Any]) -> int:
        return self.semantic.add_text(text, metadata)

    def retrieve_knowledge(self, query: str, k: int = 5) -> list[dict[str, Any]]:
        return self.semantic.search(query, k)

    def get_relevant_context(self, task_id: str, query_text: str, k: int = 3) -> dict[str, Any]:
        working_state = self.get_task_state(task_id)
        semantic_results = self.retrieve_knowledge(query_text, k)
        return {
            "working_state": working_state,
            "semantic_results": semantic_results,
        }
