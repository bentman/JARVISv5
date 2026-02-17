import os
import subprocess
import sys
from datetime import datetime


SUITES = {
    "unit": "tests/unit",
    "integration": "tests/integration",
    "agentic": "tests/agentic",
}


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
            raise ValueError("--scope requires a value: all|unit|integration|agentic")
        scope = argv[index + 1].strip().lower()

    if scope == "all":
        return ["unit", "integration", "agentic"]
    if scope in SUITES:
        return [scope]
    raise ValueError("Invalid --scope value. Use: all|unit|integration|agentic")


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
    status = "PASS" if proc.returncode == 0 else "FAIL"
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
    }
    terminal_sections: list[str] = []

    for suite_name in selected_suites:
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
        "============================================================\n\n"
        "[INVARIANTS]\n"
        f"UNIT_TESTS={statuses['unit']}\n"
        f"INTEGRATION_TESTS={statuses['integration']}\n"
        f"AGENTIC_TESTS={statuses['agentic']}\n"
    )

    with open(report_path, "w", encoding="utf-8") as handle:
        handle.write(report)

    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
