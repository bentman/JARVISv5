import json
import time
from typing import Any
from uuid import uuid4

from backend.memory.memory_manager import MemoryManager
from backend.models.hardware_profiler import HardwareService
from backend.models.model_registry import ModelRegistry
from backend.workflow import ContextBuilderNode, LLMWorkerNode, RouterNode, ToolCallNode, ValidatorNode
from backend.workflow.dag_executor import DAGExecutor, WorkflowEdge, WorkflowGraph
from backend.workflow.plan_compiler import compile_plan_to_workflow_graph

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

    def _log_dag_node_event(
        self,
        task_id: str,
        node_id: str,
        node_type: str,
        controller_state: ControllerState,
        event_type: str,
        success: bool,
        error: str | None = None,
        elapsed_ns: int | None = None,
        start_offset_ns: int | None = None,
    ) -> None:
        payload: dict[str, Any] = {
            "controller_state": controller_state.value,
            "event_type": event_type,
            "node_id": node_id,
            "node_type": node_type,
            "success": success,
            "task_id": task_id,
        }
        if error:
            payload["error"] = error
        if elapsed_ns is not None:
            payload["elapsed_ns"] = int(elapsed_ns)
        if start_offset_ns is not None:
            payload["start_offset_ns"] = int(start_offset_ns)

        self.memory.log_decision(
            task_id=task_id,
            action_type="dag_node_event",
            content=json.dumps(payload, sort_keys=True, separators=(",", ":")),
            status=event_type,
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
        tool_call: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        fsm = DeterministicFSM()
        continuation = task_id is not None
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
        if tool_call is not None:
            context["tool_call"] = tool_call
        task_started_ns = time.perf_counter_ns()

        router_node = RouterNode()
        context_builder_node = ContextBuilderNode()
        llm_worker_node = LLMWorkerNode()
        tool_call_node = ToolCallNode()
        validator_node = ValidatorNode()
        dag_executor = DAGExecutor()
        node_registry = {
            "router": router_node,
            "context_builder": context_builder_node,
            "tool_call": tool_call_node,
            "llm_worker": llm_worker_node,
            "validator": validator_node,
        }
        phase_to_nodes = {
            ControllerState.PLAN: {"router"},
            ControllerState.EXECUTE: {"context_builder", "tool_call", "llm_worker"},
            ControllerState.VALIDATE: {"validator"},
        }

        def _with_tool_call_node(graph: WorkflowGraph) -> WorkflowGraph:
            if "tool_call" in graph.nodes:
                return graph

            new_nodes = list(graph.nodes)
            if "tool_call" not in new_nodes:
                new_nodes.append("tool_call")

            new_edges: list[WorkflowEdge] = []
            inserted = False
            for edge in graph.edges:
                if edge.from_node == "context_builder" and edge.to_node == "llm_worker":
                    new_edges.append(WorkflowEdge("context_builder", "tool_call"))
                    new_edges.append(WorkflowEdge("tool_call", "llm_worker"))
                    inserted = True
                else:
                    new_edges.append(edge)

            if not inserted:
                new_edges.append(WorkflowEdge("context_builder", "tool_call"))
                new_edges.append(WorkflowEdge("tool_call", "llm_worker"))

            return WorkflowGraph(
                nodes=tuple(new_nodes),
                edges=tuple(new_edges),
                entry=graph.entry,
            )

        def _no_model_fallback_message(profile: str, hardware_type: str, role: str) -> str:
            return (
                "Local model missing. Please drop a GGUF into models/ and update the catalog. "
                "\n" 
                f"Catalog: models/models.yaml\n" 
                f"Requested role={role}, profile={profile}, hardware={hardware_type}\n" 
                "Expected example path: models/test-mini.gguf"
            )

        try:
            if continuation:
                existing_task = self.memory.get_task_state(resolved_task_id)
                if existing_task is None:
                    return self._fail(fsm, resolved_task_id, context, "task_not_found")
                self.memory.put_task_state(resolved_task_id, existing_task)
            else:
                self.memory.create_task(resolved_task_id, resolved_goal, resolved_steps)

            self.memory.append_task_message(
                resolved_task_id,
                role="user",
                content=user_input,
                max_messages=10,
            )
            self._log_state(resolved_task_id, fsm.current_state, "running")

            fsm.transition(ControllerState.PLAN)
            self.memory.update_task_status(resolved_task_id, ControllerState.PLAN.value)
            self._log_state(resolved_task_id, ControllerState.PLAN, "running")
            try:
                node_id = "router"
                node_type = node_registry[node_id].__class__.__name__
                node_started_ns = time.perf_counter_ns()
                node_start_offset_ns = max(0, node_started_ns - task_started_ns)
                self._log_dag_node_event(
                    task_id=resolved_task_id,
                    node_id=node_id,
                    node_type=node_type,
                    controller_state=ControllerState.PLAN,
                    event_type="node_start",
                    success=False,
                    start_offset_ns=node_start_offset_ns,
                )
                try:
                    context = node_registry[node_id].execute(context)
                except Exception as exc:
                    node_error_elapsed_ns = max(0, time.perf_counter_ns() - node_started_ns)
                    self._log_dag_node_event(
                        task_id=resolved_task_id,
                        node_id=node_id,
                        node_type=node_type,
                        controller_state=ControllerState.PLAN,
                        event_type="node_error",
                        success=False,
                        error=str(exc),
                        elapsed_ns=node_error_elapsed_ns,
                        start_offset_ns=node_start_offset_ns,
                    )
                    raise
                node_elapsed_ns = max(0, time.perf_counter_ns() - node_started_ns)
                self._log_dag_node_event(
                    task_id=resolved_task_id,
                    node_id=node_id,
                    node_type=node_type,
                    controller_state=ControllerState.PLAN,
                    event_type="node_end",
                    success=True,
                    elapsed_ns=node_elapsed_ns,
                    start_offset_ns=node_start_offset_ns,
                )

                graph = compile_plan_to_workflow_graph(str(context.get("intent", "")))
                if isinstance(context.get("tool_call"), dict):
                    graph = _with_tool_call_node(graph)
                execution_order = dag_executor.resolve_execution_order(graph, node_registry)
                context["workflow_graph"] = graph.as_dict()
                context["workflow_execution_order"] = execution_order

                task_state = self.memory.get_task_state(resolved_task_id)
                if isinstance(task_state, dict):
                    task_state["workflow_graph"] = graph.as_dict()
                    self.memory.put_task_state(resolved_task_id, task_state)

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
                    try:
                        model_path = self.registry.ensure_model_present(selected_model)
                        context["llm_model_path"] = model_path
                    except RuntimeError:
                        context["llm_output"] = _no_model_fallback_message(profile, hardware_type, role)
                        context["llm_error"] = "local_model_missing"
                        context["skip_llm"] = True
            except Exception as exc:
                return self._fail(fsm, resolved_task_id, context, f"router_node_error: {exc}")

            fsm.transition(ControllerState.EXECUTE)
            self.memory.update_task_status(resolved_task_id, ControllerState.EXECUTE.value)
            self._log_state(resolved_task_id, ControllerState.EXECUTE, "running")
            try:
                for node_id in execution_order:
                    if node_id not in phase_to_nodes[ControllerState.EXECUTE]:
                        continue
                    if node_id == "llm_worker" and bool(context.get("skip_llm", False)):
                        continue
                    node_type = node_registry[node_id].__class__.__name__
                    node_started_ns = time.perf_counter_ns()
                    node_start_offset_ns = max(0, node_started_ns - task_started_ns)
                    self._log_dag_node_event(
                        task_id=resolved_task_id,
                        node_id=node_id,
                        node_type=node_type,
                        controller_state=ControllerState.EXECUTE,
                        event_type="node_start",
                        success=False,
                        start_offset_ns=node_start_offset_ns,
                    )
                    try:
                        context = node_registry[node_id].execute(context)
                    except Exception as exc:
                        node_error_elapsed_ns = max(0, time.perf_counter_ns() - node_started_ns)
                        self._log_dag_node_event(
                            task_id=resolved_task_id,
                            node_id=node_id,
                            node_type=node_type,
                            controller_state=ControllerState.EXECUTE,
                            event_type="node_error",
                            success=False,
                            error=str(exc),
                            elapsed_ns=node_error_elapsed_ns,
                            start_offset_ns=node_start_offset_ns,
                        )
                        raise
                    node_elapsed_ns = max(0, time.perf_counter_ns() - node_started_ns)
                    self._log_dag_node_event(
                        task_id=resolved_task_id,
                        node_id=node_id,
                        node_type=node_type,
                        controller_state=ControllerState.EXECUTE,
                        event_type="node_end",
                        success=True,
                        elapsed_ns=node_elapsed_ns,
                        start_offset_ns=node_start_offset_ns,
                    )
            except Exception as exc:
                return self._fail(fsm, resolved_task_id, context, f"execute_node_error: {exc}")

            if not str(context.get("llm_output", "")).strip() and context.get("llm_error"):
                context["llm_output"] = str(context["llm_error"])

            llm_text = str(context.get("llm_output", "")).strip()
            if llm_text:
                self.memory.append_task_message(
                    resolved_task_id,
                    role="assistant",
                    content=llm_text,
                    max_messages=10,
                )

            fsm.transition(ControllerState.VALIDATE)
            self.memory.update_task_status(resolved_task_id, ControllerState.VALIDATE.value)
            self._log_state(resolved_task_id, ControllerState.VALIDATE, "running")
            try:
                for node_id in execution_order:
                    if node_id not in phase_to_nodes[ControllerState.VALIDATE]:
                        continue
                    node_type = node_registry[node_id].__class__.__name__
                    node_started_ns = time.perf_counter_ns()
                    node_start_offset_ns = max(0, node_started_ns - task_started_ns)
                    self._log_dag_node_event(
                        task_id=resolved_task_id,
                        node_id=node_id,
                        node_type=node_type,
                        controller_state=ControllerState.VALIDATE,
                        event_type="node_start",
                        success=False,
                        start_offset_ns=node_start_offset_ns,
                    )
                    try:
                        context = node_registry[node_id].execute(context)
                    except Exception as exc:
                        node_error_elapsed_ns = max(0, time.perf_counter_ns() - node_started_ns)
                        self._log_dag_node_event(
                            task_id=resolved_task_id,
                            node_id=node_id,
                            node_type=node_type,
                            controller_state=ControllerState.VALIDATE,
                            event_type="node_error",
                            success=False,
                            error=str(exc),
                            elapsed_ns=node_error_elapsed_ns,
                            start_offset_ns=node_start_offset_ns,
                        )
                        raise
                    node_elapsed_ns = max(0, time.perf_counter_ns() - node_started_ns)
                    self._log_dag_node_event(
                        task_id=resolved_task_id,
                        node_id=node_id,
                        node_type=node_type,
                        controller_state=ControllerState.VALIDATE,
                        event_type="node_end",
                        success=True,
                        elapsed_ns=node_elapsed_ns,
                        start_offset_ns=node_start_offset_ns,
                    )
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
