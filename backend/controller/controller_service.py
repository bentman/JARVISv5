from typing import Any

from backend.memory.memory_manager import MemoryManager

from .fsm import ControllerState, DeterministicFSM


class ControllerService:
    def __init__(self, memory_manager: MemoryManager | None = None) -> None:
        self.memory = memory_manager or MemoryManager()

    def _log_state(self, task_id: str, state: ControllerState, status: str) -> None:
        self.memory.log_decision(
            task_id=task_id,
            action_type="controller_state",
            content=state.value,
            status=status,
        )

    def run_task(
        self,
        task_id: str,
        goal: str,
        steps: list[str],
        validation_passed: bool = True,
    ) -> dict[str, Any]:
        fsm = DeterministicFSM()
        self.memory.create_task(task_id, goal, steps)
        self._log_state(task_id, fsm.current_state, "running")

        try:
            fsm.transition(ControllerState.PLAN)
            self.memory.update_task_status(task_id, ControllerState.PLAN.value)
            self._log_state(task_id, ControllerState.PLAN, "running")

            fsm.transition(ControllerState.EXECUTE)
            self.memory.update_task_status(task_id, ControllerState.EXECUTE.value)
            self._log_state(task_id, ControllerState.EXECUTE, "running")

            fsm.transition(ControllerState.VALIDATE)
            self.memory.update_task_status(task_id, ControllerState.VALIDATE.value)
            self._log_state(task_id, ControllerState.VALIDATE, "running")

            if not validation_passed:
                fsm.transition(ControllerState.FAILED)
                self.memory.update_task_status(task_id, ControllerState.FAILED.value)
                self._log_state(task_id, ControllerState.FAILED, "failed")
                return {
                    "task_id": task_id,
                    "final_state": fsm.current_state.value,
                    "archived": False,
                }

            fsm.transition(ControllerState.COMMIT)
            self.memory.update_task_status(task_id, ControllerState.COMMIT.value)
            self._log_state(task_id, ControllerState.COMMIT, "running")

            fsm.transition(ControllerState.ARCHIVE)
            self.memory.archive_task(task_id)
            self._log_state(task_id, ControllerState.ARCHIVE, "completed")

            return {
                "task_id": task_id,
                "final_state": fsm.current_state.value,
                "archived": True,
            }

        except Exception as exc:
            if fsm.can_transition(ControllerState.FAILED):
                fsm.transition(ControllerState.FAILED)
            try:
                self.memory.update_task_status(task_id, ControllerState.FAILED.value)
            except Exception:
                pass
            self._log_state(task_id, ControllerState.FAILED, "error")
            return {
                "task_id": task_id,
                "final_state": fsm.current_state.value,
                "archived": False,
                "error": str(exc),
            }
