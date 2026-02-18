import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime


SUITES = {
    "unit": "tests/unit",
    "integration": "tests/integration",
    "agentic": "tests/agentic",
}

DOCKER_SCOPE = "docker-inference"
SEPARATOR = "=" * 60


def resolve_python_executable() -> str:
    venv_python = os.path.join("backend", ".venv", "Scripts", "python")
    if os.path.exists(venv_python):
        return venv_python
    return sys.executable


def parse_scope(argv: list[str]) -> list[str]:
    scope = "all"
    if "--scope" in argv:
        index = argv.index("--scope")
        if index + 1 >= len(argv):
            raise ValueError("--scope requires a value: all|unit|integration|agentic|docker-inference")
        scope = argv[index + 1].strip().lower()

    if scope == "all":
        return ["unit", "integration", "agentic"]
    if scope == DOCKER_SCOPE:
        return [DOCKER_SCOPE]
    if scope in SUITES:
        return [scope]
    raise ValueError("Invalid --scope value. Use: all|unit|integration|agentic|docker-inference")


def run_command(command: list[str], env: dict[str, str] | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(command, capture_output=True, text=True, env=env)


def section_header(title: str) -> list[str]:
    return ["", SEPARATOR, title.upper(), SEPARATOR]


def _extract_root_cause(proc: subprocess.CompletedProcess) -> str:
    merged = ((proc.stderr or "") + "\n" + (proc.stdout or "")).strip()
    for line in merged.splitlines():
        cleaned = line.strip()
        if cleaned:
            return cleaned
    return f"return_code={proc.returncode}"


def _collected_count(output_text: str) -> int | None:
    match = re.search(r"collected\s+(\d+)\s+items", output_text)
    return int(match.group(1)) if match else None


def _parse_per_test_lines(output_text: str) -> list[str]:
    test_lines: list[str] = []
    for raw_line in output_text.splitlines():
        line = raw_line.strip()
        match = re.match(
            r"^(.+::[^\s]+)\s+(PASSED|FAILED|SKIPPED|XFAIL|XPASS|XFAILED|XPASSED)(?:\s+\[[^\]]+\])?$",
            line,
        )
        if not match:
            continue

        test_id, status = match.groups()
        if status == "PASSED":
            test_lines.append(f"  ✓ PASS: {test_id}")
        elif status == "FAILED":
            test_lines.append(f"  ✗ FAIL: {test_id}")
        elif status in {"XPASS", "XPASSED"}:
            test_lines.append(f"  ✓ PASS: {test_id}")
        else:  # SKIPPED / XFAIL / XFAILED
            test_lines.append(f"  ○ SKIP: {test_id}")
    return test_lines


def run_suite(suite_name: str, suite_path: str) -> tuple[str, list[str]]:
    section_lines = section_header(f"{suite_name} tests")
    suite_label = suite_name.capitalize()

    if not os.path.isdir(suite_path):
        section_lines.append(f"WARN: {suite_label}: Directory not found")
        return "WARN", section_lines

    command = [resolve_python_executable(), "-m", "pytest", "-v", suite_path]
    proc = run_command(command)
    output_text = ((proc.stdout or "") + (proc.stderr or "")).strip()

    if proc.returncode == 0:
        status = "PASS"
    elif proc.returncode == 5:
        status = "WARN"
    else:
        status = "FAIL"

    collected = _collected_count(output_text)
    per_test_lines = _parse_per_test_lines(output_text)
    if per_test_lines:
        total = len(per_test_lines)
        max_lines = 200
        section_lines.extend(per_test_lines[:max_lines])
        if total > max_lines:
            section_lines.append(f"... truncated ({total} total tests)")

    if status == "PASS":
        if collected is not None:
            section_lines.append(f"SUCCESS: {suite_label}: {collected} tests")
        else:
            section_lines.append(f"SUCCESS: {suite_label}: tests passed")
    elif status == "WARN":
        if proc.returncode == 5:
            section_lines.append(f"WARN: {suite_label}: No tests collected")
        else:
            section_lines.append(f"WARN: {suite_label}: Non-fatal warning")
    else:
        section_lines.append(f"FAILED: {suite_label}: pytest return code {proc.returncode}")

    return status, section_lines


def run_docker_inference_validation() -> tuple[str, list[str]]:
    steps: list[tuple[str, list[str]]] = [
        ("Compose Config", ["docker", "compose", "config"]),
        ("Build Backend", ["docker", "compose", "build", "backend"]),
        ("Start Redis+Backend", ["docker", "compose", "up", "-d", "redis", "backend"]),
        (
            "Import llama_cpp in container",
            ["docker", "compose", "exec", "-T", "backend", "python", "-c", "import llama_cpp; print('OK')"],
        ),
    ]

    section_lines = section_header("docker inference")

    for _, command in steps:
        first = run_command(command)
        if first.returncode != 0:
            second = run_command(command)
            if second.returncode != 0 and _extract_root_cause(first) == _extract_root_cause(second):
                stderr_excerpt = ((second.stderr or "") + (second.stdout or "")).strip()
                excerpt_lines = "\n".join(stderr_excerpt.splitlines()[:10])
                section_lines.append(f"Status: FAIL | Command: {' '.join(command)}")
                section_lines.append(f"FAILED: Docker Inference: {excerpt_lines}")
                return "FAIL", section_lines

            stderr_excerpt = ((second.stderr or "") + (second.stdout or "")).strip()
            excerpt_lines = "\n".join(stderr_excerpt.splitlines()[:10])
            section_lines.append(f"Status: FAIL | Command: {' '.join(command)}")
            section_lines.append(f"FAILED: Docker Inference: {excerpt_lines}")
            return "FAIL", section_lines

        section_lines.append(f"Status: PASS | Command: {' '.join(command)}")

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
        section_lines.append("Status: FAIL | Command: GET http://localhost:8000/health")
        section_lines.append("FAILED: Docker Inference: health endpoint unavailable")
        return "FAIL", section_lines

    section_lines.append("Status: PASS | Command: GET http://localhost:8000/health")

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
        section_lines.append("Status: FAIL | Command: POST http://localhost:8000/task")
        section_lines.append(f"FAILED: Docker Inference: HTTP {exc.code}: {body[:500]}")
        return "FAIL", section_lines
    except Exception as exc:
        section_lines.append("Status: FAIL | Command: POST http://localhost:8000/task")
        section_lines.append(f"FAILED: Docker Inference: {exc}")
        return "FAIL", section_lines

    try:
        task_json = json.loads(task_payload)
    except json.JSONDecodeError as exc:
        section_lines.append("Status: FAIL | Command: POST http://localhost:8000/task")
        section_lines.append(f"FAILED: Docker Inference: Invalid JSON response: {exc}")
        return "FAIL", section_lines

    llm_output = str(task_json.get("llm_output", ""))
    if len(llm_output.strip()) == 0:
        section_lines.append("Status: FAIL | Command: POST http://localhost:8000/task")
        section_lines.append("FAILED: Docker Inference: llm_output was empty")
        return "FAIL", section_lines

    section_lines.append("Status: PASS | Command: POST http://localhost:8000/task")
    section_lines.append("SUCCESS: Docker Inference: /task returned non-empty llm_output")
    return "PASS", section_lines


def build_summary_and_verdict(statuses: dict[str, str], report_path: str) -> list[str]:
    lines = section_header("backend validation summary")
    lines.append(f"Unit Tests:        {statuses['unit']}")
    lines.append(f"Integration Tests: {statuses['integration']}")
    lines.append(f"Agentic Tests:     {statuses['agentic']}")
    lines.append(f"Docker Inference:  {statuses['docker_inference']}")
    lines.append(SEPARATOR)
    lines.append("[INVARIANTS]")
    lines.append(f"UNIT_TESTS={statuses['unit']}")
    lines.append(f"INTEGRATION_TESTS={statuses['integration']}")
    lines.append(f"AGENTIC_TESTS={statuses['agentic']}")
    lines.append(f"DOCKER_INFERENCE={statuses['docker_inference']}")

    if any(status == "FAIL" for status in statuses.values()):
        lines.append(f"❌ JARVISv5 Validation failed. See report: {report_path}")
    elif any(status == "WARN" for status in statuses.values()):
        lines.append("✅ JARVISv5 Current ./backend is validated with warnings.")
    else:
        lines.append("✅ JARVISv5 Current ./backend is validated!")
    return lines


def main() -> int:
    try:
        selected_suites = parse_scope(sys.argv[1:])
    except ValueError as error:
        print(f"ERROR: {error}")
        return 2

    started_at = datetime.now()
    started_iso = started_at.isoformat(timespec="seconds")
    filename_stamp = started_at.strftime("%Y%m%d_%H%M%S")

    os.makedirs("reports", exist_ok=True)
    report_filename = f"backend_validation_report_{filename_stamp}.txt"
    report_rel_path = f"reports\\{report_filename}"
    report_path = os.path.join("reports", report_filename)

    statuses = {
        "unit": "SKIP",
        "integration": "SKIP",
        "agentic": "SKIP",
        "docker_inference": "SKIP",
    }

    lines: list[str] = [
        f"JARVISv5 Backend Validation Session started at {started_iso}",
        f"Report File: {report_rel_path}",
        SEPARATOR,
    ]

    for suite_name in selected_suites:
        if suite_name == DOCKER_SCOPE:
            status, section_lines = run_docker_inference_validation()
            statuses["docker_inference"] = status
        else:
            status, section_lines = run_suite(suite_name, SUITES[suite_name])
            statuses[suite_name] = status
        lines.extend(section_lines)

    lines.extend(build_summary_and_verdict(statuses, report_rel_path))
    output = "\n".join(lines) + "\n"

    with open(report_path, "w", encoding="utf-8") as handle:
        handle.write(output)

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print(output, end="")
    return 1 if any(status == "FAIL" for status in statuses.values()) else 0


if __name__ == "__main__":
    raise SystemExit(main())
