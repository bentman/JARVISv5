from pathlib import Path
from typing import Any
from uuid import uuid4

from backend.memory.memory_manager import MemoryManager
from backend.models.hardware_profiler import HardwareService
from backend.models.model_registry import ModelRegistry
from backend.workflow import ContextBuilderNode, LLMWorkerNode, RouterNode, ValidatorNode

from .fsm import ControllerState, DeterministicFSM


class ControllerService:
    def __init__(
        self,
        memory_manager: MemoryManager | None = None,
        hardware_service: HardwareService | None = None,
        model_registry: ModelRegistry | None = None,
    ) -> None:
        self.memory = memory_manager or MemoryManager()
        self.hardware = hardware_service or HardwareService()
        self.registry = model_registry or ModelRegistry()

    def _log_state(self, task_id: str, state: ControllerState, status: str) -> None:
        self.memory.log_decision(
            task_id=task_id,
            action_type="controller_state",
            content=state.value,
            status=status,
        )

    def _fail(
        self,
        fsm: DeterministicFSM,
        task_id: str,
        context: dict[str, Any],
        error: str,
    ) -> dict[str, Any]:
        if fsm.can_transition(ControllerState.FAILED):
            fsm.transition(ControllerState.FAILED)
        try:
            self.memory.update_task_status(task_id, ControllerState.FAILED.value)
        except Exception:
            pass
        self._log_state(task_id, ControllerState.FAILED, "error")
        context.setdefault("llm_output", error)
        context.setdefault("controller_error", error)
        return {
            "task_id": task_id,
            "final_state": fsm.current_state.value,
            "archived": False,
            "context": context,
            "error": error,
        }

    def run(
        self,
        user_input: str,
        task_id: str | None = None,
        goal: str | None = None,
        steps: list[str] | None = None,
    ) -> dict[str, Any]:
        fsm = DeterministicFSM()
        resolved_task_id = task_id or f"task-{uuid4().hex[:10]}"
        resolved_goal = goal or "Process user input through deterministic workflow"
        resolved_steps = steps or [
            ControllerState.PLAN.value,
            ControllerState.EXECUTE.value,
            ControllerState.VALIDATE.value,
            ControllerState.COMMIT.value,
            ControllerState.ARCHIVE.value,
        ]

        context: dict[str, Any] = {
            "user_input": user_input,
            "task_id": resolved_task_id,
            "memory_manager": self.memory,
        }

        router_node = RouterNode()
        context_builder_node = ContextBuilderNode()
        llm_worker_node = LLMWorkerNode()
        validator_node = ValidatorNode()

        def _no_model_fallback_message(profile: str, hardware_type: str, role: str) -> str:
            return (
                "Local model missing. Please drop a GGUF into models/ and update the catalog. "
                "\n" 
                f"Catalog: models/models.yaml\n" 
                f"Requested role={role}, profile={profile}, hardware={hardware_type}\n" 
                "Expected example path: models/test-mini.gguf"
            )

        try:
            self.memory.create_task(resolved_task_id, resolved_goal, resolved_steps)
            self._log_state(resolved_task_id, fsm.current_state, "running")

            fsm.transition(ControllerState.PLAN)
            self.memory.update_task_status(resolved_task_id, ControllerState.PLAN.value)
            self._log_state(resolved_task_id, ControllerState.PLAN, "running")
            try:
                context = router_node.execute(context)

                profile = self.hardware.get_hardware_profile()
                hardware_type = self.hardware.detect_hardware_type().value
                role = "code" if str(context.get("intent", "")) == "code" else "chat"
                selected_model = self.registry.select_model(
                    profile=profile,
                    hardware=hardware_type,
                    role=role,
                )
                if selected_model is None:
                    context["selected_model"] = None
                    context["llm_model_path"] = ""
                    context["llm_output"] = _no_model_fallback_message(profile, hardware_type, role)
                    context["llm_error"] = "local_model_missing"
                    context["skip_llm"] = True
                else:
                    context["selected_model"] = selected_model
                    model_path = str(selected_model.get("path", ""))
                    context["llm_model_path"] = model_path

                    if not model_path or not Path(model_path).exists():
                        context["llm_output"] = _no_model_fallback_message(profile, hardware_type, role)
                        context["llm_error"] = "local_model_missing"
                        context["skip_llm"] = True
            except Exception as exc:
                return self._fail(fsm, resolved_task_id, context, f"router_node_error: {exc}")

            fsm.transition(ControllerState.EXECUTE)
            self.memory.update_task_status(resolved_task_id, ControllerState.EXECUTE.value)
            self._log_state(resolved_task_id, ControllerState.EXECUTE, "running")
            try:
                context = context_builder_node.execute(context)
                if not bool(context.get("skip_llm", False)):
                    context = llm_worker_node.execute(context)
            except Exception as exc:
                return self._fail(fsm, resolved_task_id, context, f"execute_node_error: {exc}")

            if not str(context.get("llm_output", "")).strip() and context.get("llm_error"):
                context["llm_output"] = str(context["llm_error"])

            fsm.transition(ControllerState.VALIDATE)
            self.memory.update_task_status(resolved_task_id, ControllerState.VALIDATE.value)
            self._log_state(resolved_task_id, ControllerState.VALIDATE, "running")
            try:
                context = validator_node.execute(context)
            except Exception as exc:
                return self._fail(fsm, resolved_task_id, context, f"validator_node_error: {exc}")

            if not bool(context.get("is_valid", False)):
                return self._fail(fsm, resolved_task_id, context, "validation_failed")

            fsm.transition(ControllerState.COMMIT)
            self.memory.update_task_status(resolved_task_id, ControllerState.COMMIT.value)
            self._log_state(resolved_task_id, ControllerState.COMMIT, "running")

            fsm.transition(ControllerState.ARCHIVE)
            self.memory.archive_task(resolved_task_id)
            self._log_state(resolved_task_id, ControllerState.ARCHIVE, "completed")

            return {
                "task_id": resolved_task_id,
                "final_state": fsm.current_state.value,
                "archived": True,
                "context": context,
            }

        except Exception as exc:
            return self._fail(fsm, resolved_task_id, context, str(exc))

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
