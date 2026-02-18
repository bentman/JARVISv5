import os
import subprocess
import sys
import time
import json
import urllib.error
import urllib.request
from datetime import datetime


SUITES = {
    "unit": "tests/unit",
    "integration": "tests/integration",
    "agentic": "tests/agentic",
}

DOCKER_SCOPE = "docker-inference"


def resolve_python_executable() -> str:
    """Resolve the Python executable to use for validation runs.

    Policy:
    - Prefer repo-local venv `backend/.venv` on Windows (per AGENTS.md).
    - If not present (e.g., running inside Docker), fall back to current interpreter.
    """

    venv_python = os.path.join("backend", ".venv", "Scripts", "python")
    if os.path.exists(venv_python):
        return venv_python
    return sys.executable


def parse_scope(argv: list[str]) -> list[str]:
    scope = "all"
    if "--scope" in argv:
        index = argv.index("--scope")
        if index + 1 >= len(argv):
            raise ValueError(
                "--scope requires a value: all|unit|integration|agentic|docker-inference"
            )
        scope = argv[index + 1].strip().lower()

    if scope == "all":
        return ["unit", "integration", "agentic"]
    if scope == DOCKER_SCOPE:
        return [DOCKER_SCOPE]
    if scope in SUITES:
        return [scope]
    raise ValueError(
        "Invalid --scope value. Use: all|unit|integration|agentic|docker-inference"
    )


def run_command(command: list[str], env: dict[str, str] | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(command, capture_output=True, text=True, env=env)


def _extract_root_cause(proc: subprocess.CompletedProcess) -> str:
    merged = ((proc.stderr or "") + "\n" + (proc.stdout or "")).strip()
    for line in merged.splitlines():
        cleaned = line.strip()
        if cleaned:
            return cleaned
    return f"return_code={proc.returncode}"


def run_docker_inference_validation() -> tuple[str, str]:
    steps: list[tuple[str, list[str]]] = [
        ("Compose Config", ["docker", "compose", "config"]),
        ("Build Backend", ["docker", "compose", "build", "backend"]),
        ("Start Redis+Backend", ["docker", "compose", "up", "-d", "redis", "backend"]),
        (
            "Import llama_cpp in container",
            [
                "docker",
                "compose",
                "exec",
                "-T",
                "backend",
                "python",
                "-c",
                "import llama_cpp; print('OK')",
            ],
        ),
    ]

    section_lines: list[str] = ["===== DOCKER-INFERENCE SCOPE ====="]

    for label, command in steps:
        section_lines.append(f"Step: {label}")
        section_lines.append(f"Command: {' '.join(command)}")

        first = run_command(command)
        if first.returncode != 0:
            second = run_command(command)
            if second.returncode != 0 and _extract_root_cause(first) == _extract_root_cause(second):
                stderr_excerpt = ((second.stderr or "") + (second.stdout or "")).strip()
                excerpt_lines = "\n".join(stderr_excerpt.splitlines()[:10])
                section_lines.append("Status: FAIL")
                section_lines.append(f"Failing Command: {' '.join(command)}")
                section_lines.append(f"Stderr Excerpt:\n{excerpt_lines}")
                section_lines.append(
                    "Proposed Adjustment: Verify Docker daemon availability, compose service names, and container startup health before rerun."
                )
                return "FAIL", "\n".join(section_lines)

            stderr_excerpt = ((second.stderr or "") + (second.stdout or "")).strip()
            excerpt_lines = "\n".join(stderr_excerpt.splitlines()[:10])
            section_lines.append("Status: FAIL")
            section_lines.append(f"Failing Command: {' '.join(command)}")
            section_lines.append(f"Stderr Excerpt:\n{excerpt_lines}")
            return "FAIL", "\n".join(section_lines)

        merged_output = ((first.stdout or "") + (first.stderr or "")).strip()
        excerpt = "\n".join(merged_output.splitlines()[:3])
        section_lines.append("Status: PASS")
        if excerpt:
            section_lines.append(f"Output Excerpt:\n{excerpt}")

    health_url = "http://localhost:8000/health"
    health_payload = ""
    for _ in range(20):
        try:
            with urllib.request.urlopen(health_url, timeout=10) as response:
                health_payload = response.read().decode("utf-8", errors="replace")
            break
        except Exception:
            time.sleep(1)

    if not health_payload:
        section_lines.append("Step: Health Check")
        section_lines.append("Command: GET http://localhost:8000/health")
        section_lines.append("Status: FAIL")
        section_lines.append("Failing Command: GET http://localhost:8000/health")
        section_lines.append("Stderr Excerpt:\nHealth endpoint did not become available within timeout")
        section_lines.append(
            "Proposed Adjustment: Increase backend readiness wait or inspect `docker compose logs backend` for startup failures."
        )
        return "FAIL", "\n".join(section_lines)

    section_lines.append("Step: Health Check")
    section_lines.append("Command: GET http://localhost:8000/health")
    section_lines.append("Status: PASS")
    section_lines.append(f"Output Excerpt:\n{health_payload}")

    task_url = "http://localhost:8000/task"
    request_body = json.dumps({"user_input": "Reply with exactly: OK"}).encode("utf-8")
    request = urllib.request.Request(
        task_url,
        data=request_body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            task_payload = response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace") if exc.fp is not None else ""
        section_lines.append("Step: Task Inference")
        section_lines.append("Command: POST http://localhost:8000/task")
        section_lines.append("Status: FAIL")
        section_lines.append("Failing Command: POST http://localhost:8000/task")
        section_lines.append(f"Stderr Excerpt:\nHTTP {exc.code}: {body[:500]}")
        section_lines.append(
            "Proposed Adjustment: Check backend logs for inference/model loading errors and confirm mounted model path inside container."
        )
        return "FAIL", "\n".join(section_lines)
    except Exception as exc:
        section_lines.append("Step: Task Inference")
        section_lines.append("Command: POST http://localhost:8000/task")
        section_lines.append("Status: FAIL")
        section_lines.append("Failing Command: POST http://localhost:8000/task")
        section_lines.append(f"Stderr Excerpt:\n{exc}")
        section_lines.append(
            "Proposed Adjustment: Confirm backend is reachable on localhost:8000 and retry after backend readiness."
        )
        return "FAIL", "\n".join(section_lines)

    try:
        task_json = json.loads(task_payload)
    except json.JSONDecodeError as exc:
        section_lines.append("Step: Task Inference")
        section_lines.append("Command: POST http://localhost:8000/task")
        section_lines.append("Status: FAIL")
        section_lines.append("Failing Command: POST http://localhost:8000/task")
        section_lines.append(f"Stderr Excerpt:\nInvalid JSON response: {exc}")
        return "FAIL", "\n".join(section_lines)

    llm_output = str(task_json.get("llm_output", ""))
    llm_len = len(llm_output.strip())
    if llm_len == 0:
        section_lines.append("Step: Task Inference")
        section_lines.append("Command: POST http://localhost:8000/task")
        section_lines.append("Status: FAIL")
        section_lines.append("Failing Command: POST http://localhost:8000/task")
        section_lines.append("Stderr Excerpt:\nllm_output was empty")
        section_lines.append(
            "Proposed Adjustment: Verify MODEL_FETCH behavior and backend model path visibility inside container."
        )
        return "FAIL", "\n".join(section_lines)

    snippet = llm_output.strip().replace("\n", " ")[:120]
    section_lines.append("Step: Task Inference")
    section_lines.append("Command: POST http://localhost:8000/task")
    section_lines.append("Status: PASS")
    section_lines.append(f"Output Excerpt:\nllm_output_length={llm_len}; llm_output_snippet={snippet}")

    return "PASS", "\n".join(section_lines)


def run_suite(suite_name: str, suite_path: str) -> tuple[str, str]:
    if not os.path.isdir(suite_path):
        terminal_output = (
            f"===== {suite_name.upper()} SUITE =====\n"
            f"Path: {suite_path}\n"
            "WARN: Directory not found / Infrastructure in development\n"
        )
        return "WARN", terminal_output

    command = [
        resolve_python_executable(),
        "-m",
        "pytest",
        suite_path,
    ]

    proc = subprocess.run(command, capture_output=True, text=True)
    if proc.returncode == 0:
        status = "PASS"
    elif proc.returncode == 5:
        status = "WARN"
    else:
        status = "FAIL"
    output_text = (proc.stdout or "") + (proc.stderr or "")

    terminal_output = (
        f"===== {suite_name.upper()} SUITE =====\n"
        f"Command: {' '.join(command)}\n"
        f"Return Code: {proc.returncode}\n"
        f"Status: {status}\n"
        f"{output_text.rstrip()}\n"
    )
    return status, terminal_output


def main() -> int:
    try:
        selected_suites = parse_scope(sys.argv[1:])
    except ValueError as error:
        print(f"ERROR: {error}")
        return 2

    started_at = datetime.now()
    timestamp_text = started_at.strftime("%Y-%m-%d %H:%M:%S")
    filename_stamp = started_at.strftime("%Y%m%d_%H%M%S")

    os.makedirs("reports", exist_ok=True)
    report_filename = f"backend_validation_report_{filename_stamp}.txt"
    report_path = os.path.join("reports", report_filename)

    statuses = {
        "unit": "WARN",
        "integration": "WARN",
        "agentic": "WARN",
        "docker_inference": "WARN",
    }
    terminal_sections: list[str] = []

    for suite_name in selected_suites:
        if suite_name == DOCKER_SCOPE:
            status, terminal_output = run_docker_inference_validation()
            statuses["docker_inference"] = status
        else:
            status, terminal_output = run_suite(suite_name, SUITES[suite_name])
            statuses[suite_name] = status
        terminal_sections.append(terminal_output)

    terminal_block = "\n".join(terminal_sections).rstrip()

    report = (
        f"JARVISv5 Backend Validation Session started at {timestamp_text}\n"
        f"Report File: {report_filename}\n"
        "============================================================\n\n"
        f"{terminal_block}\n\n"
        "============================================================\n"
        "[SUMMARY SECTION]\n"
        f"Unit Tests: {statuses['unit']}\n"
        f"Integration Tests: {statuses['integration']}\n"
        f"Agentic Tests: {statuses['agentic']}\n"
        f"Docker Inference: {statuses['docker_inference']}\n"
        "============================================================\n\n"
        "[INVARIANTS]\n"
        f"UNIT_TESTS={statuses['unit']}\n"
        f"INTEGRATION_TESTS={statuses['integration']}\n"
        f"AGENTIC_TESTS={statuses['agentic']}\n"
        f"DOCKER_INFERENCE={statuses['docker_inference']}\n"
    )

    with open(report_path, "w", encoding="utf-8") as handle:
        handle.write(report)

    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
