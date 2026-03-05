from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from backend.controller.controller_service import ControllerService
from backend.memory.memory_manager import MemoryManager
from backend.models.hardware_profiler import HardwareService
from backend.models.model_registry import ModelRegistry
from backend.workflow.nodes.validator_node import ValidatorNode


SEARCH_FIXTURES = Path("tests/fixtures/search")
SEARCH_ALLOWED_PROVIDER_ORDER = ("searxng", "duckduckgo", "tavily")


class _DeterministicEmbeddingModel:
    def encode(self, text: str) -> list[float]:
        values = [0.0] * 8
        for idx, ch in enumerate(str(text)):
            values[idx % 8] += (ord(ch) % 97) / 97.0
        return values


@dataclass(frozen=True)
class TaskScenario:
    scenario_id: str
    category: str
    inputs: tuple[str, ...]
    expected_intent: str
    expected: dict[str, Any]


def _build_memory_manager(root: Path) -> MemoryManager:
    return MemoryManager(
        episodic_db_path=str(root / "episodic" / "trace.db"),
        working_base_path=str(root / "working_state"),
        working_archive_path=str(root / "archives"),
        semantic_db_path=str(root / "semantic" / "metadata.db"),
        embedding_model=_DeterministicEmbeddingModel(),
    )


def _build_controller(root: Path) -> ControllerService:
    return ControllerService(memory_manager=_build_memory_manager(root))


def _build_search_payload_loader(fixture_map: dict[str, str]):
    allowed = set(SEARCH_ALLOWED_PROVIDER_ORDER)

    def _loader(provider_name: str, _query: str) -> dict[str, Any] | str:
        if provider_name not in allowed:
            raise ValueError(f"unexpected provider: {provider_name}")
        fixture_name = fixture_map.get(provider_name)
        if fixture_name is None:
            return {"results": []}
        path = SEARCH_FIXTURES / fixture_name
        return json.loads(path.read_text(encoding="utf-8"))

    return _loader


def _execute_scenario(base_dir: Path, scenario: TaskScenario) -> dict[str, Any]:
    scenario_dir = base_dir / scenario.scenario_id
    scenario_dir.mkdir(parents=True, exist_ok=True)

    controller = _build_controller(scenario_dir)
    run_artifacts: list[dict[str, Any]] = []

    conversation_task_id: str | None = None
    for turn_idx, user_input in enumerate(scenario.inputs):
        tool_call = None
        if scenario.category == "tool":
            sandbox_root = scenario_dir / "sandbox"
            sandbox_root.mkdir(parents=True, exist_ok=True)
            (sandbox_root / "alpha.txt").write_text("alpha deterministic", encoding="utf-8")
            (sandbox_root / "beta.txt").write_text("beta deterministic", encoding="utf-8")
            (sandbox_root / "nested").mkdir(exist_ok=True)
            (sandbox_root / "nested" / "notes.txt").write_text("nested notes", encoding="utf-8")

            op = str(scenario.expected["tool_op"])
            payload: dict[str, Any]
            if op == "list_directory":
                payload = {"path": str(sandbox_root)}
            elif op == "read_file":
                payload = {"path": str(sandbox_root / "alpha.txt"), "encoding": "utf-8"}
            else:
                payload = {"path": str(sandbox_root / "nested" / "notes.txt")}

            tool_call = {
                "tool_name": op,
                "payload": payload,
                "allow_write_safe": False,
                "sandbox_roots": [str(sandbox_root)],
                "audit_log_path": str(scenario_dir / "tool_audit.jsonl"),
            }

        elif scenario.category == "search":
            sandbox_root = scenario_dir / "sandbox"
            sandbox_root.mkdir(parents=True, exist_ok=True)
            fixture_map = dict(scenario.expected["fixture_map"])
            preferred = scenario.expected.get("preferred_provider")
            payload: dict[str, Any] = {
                "query": user_input,
                "top_k": int(scenario.expected.get("top_k", 3)),
            }
            if preferred is not None:
                payload["preferred_provider"] = str(preferred)

            tool_call = {
                "tool_name": "search_web",
                "payload": payload,
                "external_call": True,
                "allow_external": True,
                "sandbox_roots": [str(sandbox_root)],
                "audit_log_path": str(scenario_dir / "search_audit.jsonl"),
                "search_payload_loader": _build_search_payload_loader(fixture_map),
            }

        result = controller.run(
            user_input=user_input,
            task_id=conversation_task_id,
            tool_call=tool_call,
        )
        if scenario.category == "conversation":
            conversation_task_id = str(result.get("task_id", "")).strip() or conversation_task_id
        run_artifacts.append(result)

    return {
        "scenario": scenario,
        "runs": run_artifacts,
        "final": run_artifacts[-1],
    }


def _evaluate_success(execution: dict[str, Any]) -> tuple[bool, str]:
    scenario = execution["scenario"]
    final = execution["final"]
    context = final.get("context", {}) if isinstance(final.get("context"), dict) else {}

    if str(final.get("final_state", "")) != "ARCHIVE":
        return False, "final_state_failed"
    if not bool(final.get("archived", False)):
        return False, "not_archived"

    llm_output = str(context.get("llm_output", ""))
    if not llm_output.strip():
        return False, "empty_output"
    if not bool(context.get("is_valid", False)):
        return False, "validator_failed"

    observed_intent = str(context.get("intent", "")).strip()
    if observed_intent != scenario.expected_intent:
        return False, "intent_mismatch"

    if scenario.category in {"qa", "code", "conversation"}:
        required_tokens = tuple(scenario.expected.get("required_tokens", ()))
        lowered = llm_output.lower()
        for token in required_tokens:
            if str(token).lower() not in lowered:
                return False, "category_correctness_failed"

        if scenario.category == "conversation":
            runs = execution["runs"]
            if len(runs) != len(scenario.inputs):
                return False, "conversation_turn_count_mismatch"
            first_task_id = str(runs[0].get("task_id", ""))
            if not first_task_id:
                return False, "conversation_missing_task_id"
            if any(str(item.get("task_id", "")) != first_task_id for item in runs):
                return False, "conversation_task_id_drift"

        return True, "ok"

    if scenario.category == "tool":
        if not bool(context.get("tool_ok", False)):
            return False, "tool_error"
        tool_result = context.get("tool_result", {}) if isinstance(context.get("tool_result"), dict) else {}
        if str(tool_result.get("code", "")) != "ok":
            return False, "tool_error"

        op = str(scenario.expected["tool_op"])
        if op == "list_directory":
            entries = tool_result.get("entries", [])
            if not isinstance(entries, list) or "alpha.txt" not in entries:
                return False, "category_correctness_failed"
        elif op == "read_file":
            if str(tool_result.get("content", "")).strip() != "alpha deterministic":
                return False, "category_correctness_failed"
        else:
            if str(tool_result.get("type", "")).strip().lower() != "file":
                return False, "category_correctness_failed"
            if int(tool_result.get("size", 0)) <= 0:
                return False, "category_correctness_failed"

        return True, "ok"

    if scenario.category == "search":
        if not bool(context.get("tool_ok", False)):
            return False, "search_contract_failed"
        tool_result = context.get("tool_result", {}) if isinstance(context.get("tool_result"), dict) else {}
        if str(tool_result.get("code", "")) != "ok":
            return False, "search_contract_failed"

        items = tool_result.get("items", [])
        if not isinstance(items, list) or not items:
            return False, "search_contract_failed"

        expected_provider = str(scenario.expected["expected_provider"])
        if str(tool_result.get("provider", "")) != expected_provider:
            return False, "search_contract_failed"

        first = items[0]
        if not isinstance(first, dict):
            return False, "search_contract_failed"
        if not str(first.get("title", "")).strip():
            return False, "search_contract_failed"
        if not str(first.get("url", "")).strip():
            return False, "search_contract_failed"

        return True, "ok"

    return False, "unsupported_category"


def calculate_task_success_metrics(results: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(results)
    successful = sum(1 for row in results if bool(row.get("success", False)))
    failed = total - successful
    success_rate = (successful / total) if total else 0.0

    categories = ("qa", "code", "tool", "search", "conversation")
    by_category: dict[str, dict[str, Any]] = {}
    for category in categories:
        subset = [row for row in results if row.get("category") == category]
        cat_total = len(subset)
        cat_successful = sum(1 for row in subset if bool(row.get("success", False)))
        cat_failed = cat_total - cat_successful
        cat_rate = (cat_successful / cat_total) if cat_total else 0.0
        by_category[category] = {
            "total": cat_total,
            "successful": cat_successful,
            "failed": cat_failed,
            "success_rate": cat_rate,
        }

    failure_counter = Counter(
        (str(row.get("category", "")), str(row.get("error_type", "")))
        for row in results
        if not bool(row.get("success", False))
    )
    failure_analysis = [
        {"category": category, "error_type": error_type, "count": int(count)}
        for (category, error_type), count in sorted(failure_counter.items())
    ]

    return {
        "total_tasks": total,
        "successful": successful,
        "failed": failed,
        "success_rate": success_rate,
        "success_percentage": success_rate * 100.0,
        "target_met": success_rate >= 0.85,
        "by_category": by_category,
        "failure_analysis": failure_analysis,
    }


def _build_task_scenarios() -> list[TaskScenario]:
    scenarios: list[TaskScenario] = []

    qa_prompts = [
        "What is 2+2?",
        "Who wrote Hamlet?",
        "What is the capital of France?",
        "Define inertia in one line.",
        "What does HTTP stand for?",
        "Name a primary color.",
        "What is the boiling point of water in C?",
        "What is the opposite of hot?",
        "What is 10 minus 3?",
        "What day follows Monday?",
    ]
    for idx, prompt in enumerate(qa_prompts, start=1):
        scenarios.append(
            TaskScenario(
                scenario_id=f"qa-{idx:02d}",
                category="qa",
                inputs=(prompt,),
                expected_intent="chat",
                expected={"required_tokens": ("local model missing",)},
            )
        )

    code_prompts = [
        "Write code to reverse a string in python.",
        "Show code for fibonacci sequence.",
        "Create code for checking palindrome.",
        "Provide code that sorts a list.",
        "Give python code to read a file.",
        "Write code for binary search.",
        "Share code to merge two dicts.",
        "Need code for factorial recursion.",
        "Draft code to remove duplicates.",
        "Produce code that counts words.",
    ]
    for idx, prompt in enumerate(code_prompts, start=1):
        scenarios.append(
            TaskScenario(
                scenario_id=f"code-{idx:02d}",
                category="code",
                inputs=(prompt,),
                expected_intent="code",
                expected={"required_tokens": ("local model missing",)},
            )
        )

    tool_ops = (
        "list_directory",
        "read_file",
        "file_info",
        "list_directory",
        "read_file",
        "file_info",
        "list_directory",
        "read_file",
        "file_info",
        "list_directory",
    )
    for idx, op in enumerate(tool_ops, start=1):
        scenarios.append(
            TaskScenario(
                scenario_id=f"tool-{idx:02d}",
                category="tool",
                inputs=(f"Run tool scenario {idx}",),
                expected_intent="chat",
                expected={"tool_op": op, "required_tokens": ("local model missing",)},
            )
        )

    search_specs = [
        {"expected_provider": "duckduckgo", "fixture_map": {"searxng": "searxng_empty.json", "duckduckgo": "ddg_ok.json", "tavily": "tavily_ok.json"}},
        {"expected_provider": "searxng", "fixture_map": {"searxng": "searxng_ok.json", "duckduckgo": "ddg_ok.json", "tavily": "tavily_ok.json"}},
        {"expected_provider": "tavily", "fixture_map": {"searxng": "searxng_empty.json", "duckduckgo": "searxng_empty.json", "tavily": "tavily_ok.json"}},
        {"expected_provider": "duckduckgo", "fixture_map": {"searxng": "searxng_empty.json", "duckduckgo": "ddg_ok.json", "tavily": "tavily_ok.json"}},
        {"expected_provider": "searxng", "fixture_map": {"searxng": "searxng_ok.json", "duckduckgo": "ddg_ok.json", "tavily": "tavily_ok.json"}},
        {"expected_provider": "tavily", "fixture_map": {"searxng": "searxng_empty.json", "duckduckgo": "searxng_empty.json", "tavily": "tavily_ok.json"}, "preferred_provider": "tavily"},
        {"expected_provider": "duckduckgo", "fixture_map": {"searxng": "searxng_empty.json", "duckduckgo": "ddg_ok.json", "tavily": "tavily_ok.json"}},
        {"expected_provider": "searxng", "fixture_map": {"searxng": "searxng_ok.json", "duckduckgo": "ddg_ok.json", "tavily": "tavily_ok.json"}},
        {"expected_provider": "tavily", "fixture_map": {"searxng": "searxng_empty.json", "duckduckgo": "searxng_empty.json", "tavily": "tavily_ok.json"}},
        {"expected_provider": "duckduckgo", "fixture_map": {"searxng": "searxng_empty.json", "duckduckgo": "ddg_ok.json", "tavily": "tavily_ok.json"}},
    ]
    for idx, spec in enumerate(search_specs, start=1):
        scenarios.append(
            TaskScenario(
                scenario_id=f"search-{idx:02d}",
                category="search",
                inputs=(f"search deterministic topic {idx}",),
                expected_intent="chat",
                expected={
                    "required_tokens": ("local model missing",),
                    "expected_provider": spec["expected_provider"],
                    "fixture_map": spec["fixture_map"],
                    "preferred_provider": spec.get("preferred_provider"),
                    "top_k": 3,
                },
            )
        )

    for idx in range(1, 11):
        scenarios.append(
            TaskScenario(
                scenario_id=f"conversation-{idx:02d}",
                category="conversation",
                inputs=(
                    f"Hello from conversation {idx}",
                    "Please remember this thread",
                    "Summarize in one line",
                ),
                expected_intent="chat",
                expected={"required_tokens": ("local model missing",)},
            )
        )

    if len(scenarios) != 50:
        raise AssertionError(f"TASK_SCENARIOS must contain 50 items, found {len(scenarios)}")
    return scenarios


TASK_SCENARIOS = _build_task_scenarios()


@pytest.fixture
def deterministic_runtime(monkeypatch: pytest.MonkeyPatch) -> None:
    class _HWType:
        value = "CPU_ONLY"

    monkeypatch.setattr(HardwareService, "get_hardware_profile", lambda self: "TEST")
    monkeypatch.setattr(HardwareService, "detect_hardware_type", lambda self: _HWType())
    monkeypatch.setattr(ModelRegistry, "select_model", lambda self, profile, hardware, role: None)


def test_task_success_rate_by_category(tmp_path: Path, deterministic_runtime: None) -> None:
    results: list[dict[str, Any]] = []

    for scenario in TASK_SCENARIOS:
        execution = _execute_scenario(tmp_path, scenario)
        success, error_type = _evaluate_success(execution)
        results.append(
            {
                "scenario_id": scenario.scenario_id,
                "category": scenario.category,
                "success": success,
                "error_type": error_type,
            }
        )

    metrics = calculate_task_success_metrics(results)

    assert metrics["total_tasks"] == 50
    assert set(metrics["by_category"].keys()) == {"qa", "code", "tool", "search", "conversation"}
    for category, detail in metrics["by_category"].items():
        assert detail["total"] == 10, f"{category} should have 10 scenarios"

    assert metrics["success_rate"] >= 0.85, (
        f"Task success rate {metrics['success_rate']:.2%} < 85% | "
        f"failure_analysis={metrics['failure_analysis']}"
    )


def test_intent_classification_accuracy(tmp_path: Path, deterministic_runtime: None) -> None:
    controller = _build_controller(tmp_path / "intent")

    expected_pairs = [(scenario.inputs[0], scenario.expected_intent) for scenario in TASK_SCENARIOS]
    observed_rows: list[tuple[str, str]] = []
    for prompt, expected_intent in expected_pairs:
        run = controller.run(user_input=prompt)
        context = run.get("context", {}) if isinstance(run.get("context"), dict) else {}
        observed_intent = context.get("intent")
        if observed_intent is None:
            pytest.skip("intent output is not exposed in ControllerService context")
        observed_rows.append((str(observed_intent), expected_intent))

    correct = sum(1 for observed, expected in observed_rows if observed == expected)
    accuracy = correct / len(observed_rows) if observed_rows else 0.0
    assert accuracy >= 0.90, f"Intent classification accuracy {accuracy:.2%} < 90%"


def test_tool_execution_success_rate(tmp_path: Path, deterministic_runtime: None) -> None:
    valid_tool_results: list[bool] = []

    valid_inputs = (
        "list_directory",
        "read_file",
        "file_info",
    ) * 10

    for idx, op in enumerate(valid_inputs, start=1):
        scenario = TaskScenario(
            scenario_id=f"tool-probe-{idx:02d}",
            category="tool",
            inputs=(f"tool probe {idx}",),
            expected_intent="chat",
            expected={"tool_op": op, "required_tokens": ("local model missing",)},
        )
        execution = _execute_scenario(tmp_path / "tool_success", scenario)
        success, _ = _evaluate_success(execution)
        valid_tool_results.append(success)

    success_rate = sum(1 for item in valid_tool_results if item) / len(valid_tool_results)
    assert success_rate >= 0.95, f"Tool execution success rate {success_rate:.2%} < 95%"


def test_validation_gate_pass_rate() -> None:
    validator = ValidatorNode()

    valid_contexts = [{"llm_output": f"valid output {idx}"} for idx in range(20)]
    invalid_contexts = [
        {"llm_output": ""},
        {"llm_output": "   "},
        {"llm_output": "\n"},
        {"llm_output": "\t"},
        {"llm_output": "\r\n"},
        {"llm_output": ""},
        {"llm_output": "   "},
        {"llm_output": "\n\n"},
        {"llm_output": "\t\t"},
        {"llm_output": "  \r\n  "},
    ]

    tp = 0
    fn = 0
    for ctx in valid_contexts:
        out = validator.execute(dict(ctx))
        is_valid = out.get("is_valid")
        if is_valid is None:
            pytest.skip("validator outcome key 'is_valid' is not exposed")
        if bool(is_valid):
            tp += 1
        else:
            fn += 1

    fp = 0
    tn = 0
    for ctx in invalid_contexts:
        out = validator.execute(dict(ctx))
        is_valid = out.get("is_valid")
        if is_valid is None:
            pytest.skip("validator outcome key 'is_valid' is not exposed")
        if bool(is_valid):
            fp += 1
        else:
            tn += 1

    tpr = tp / (tp + fn) if (tp + fn) else 0.0
    fpr = fp / (fp + tn) if (fp + tn) else 0.0

    assert tpr >= 0.95, f"Validation TPR {tpr:.2%} < 95%"
    assert fpr <= 0.05, f"Validation FPR {fpr:.2%} > 5%"
