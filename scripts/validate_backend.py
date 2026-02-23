"""
JARVISv5 Backend Validation Suite
Comprehensive validation with per-test visibility, Docker inference checks, and timestamped reports.
"""
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from pathlib import Path


SUITES = {
    "unit": "tests/unit",
    "integration": "tests/integration",
    "agentic": "tests/agentic",
}

DOCKER_SCOPE = "docker-inference"
ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")


def resolve_python_executable() -> str:
    """Get Python executable, preferring venv if available"""
    venv_python = os.path.join("backend", ".venv", "Scripts", "python")
    if os.path.exists(venv_python):
        return venv_python
    return sys.executable


class ValidationLogger:
    """Handles terminal output and file-based reporting"""
    def __init__(self):
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.report_dir = Path("reports")
        self.report_dir.mkdir(exist_ok=True)
        self.report_file = self.report_dir / f"backend_validation_report_{self.timestamp}.txt"
        self.buffer = []
        
        self.log(f"JARVISv5 Backend Validation Session started at {datetime.now().isoformat()}")
        self.log(f"Report File: {self.report_file}")
        self.log("="*60)

    def log(self, message: str):
        """Log message to both terminal and buffer"""
        print(message)
        self.buffer.append(message)
    
    def header(self, title: str):
        """Print section header"""
        self.log("\n" + "="*60)
        self.log(title.upper())
        self.log("="*60)

    def save(self):
        """Write buffer to report file"""
        with open(self.report_file, "w", encoding="utf-8") as f:
            f.write("\n".join(self.buffer))
        print(f"\n[SUCCESS] Report saved to {self.report_file}")


def parse_scope(argv: list[str]) -> list[str]:
    """Parse --scope argument"""
    scope = "all"
    if "--scope" in argv:
        index = argv.index("--scope")
        if index + 1 >= len(argv):
            raise ValueError("--scope requires a value: all|unit|integration|agentic|docker-inference")
        scope = argv[index + 1].strip().lower()

    if scope == "all":
        return ["unit", "integration", "agentic", DOCKER_SCOPE]
    if scope == DOCKER_SCOPE:
        return [DOCKER_SCOPE]
    if scope in SUITES:
        return [scope]
    raise ValueError("Invalid --scope value. Use: all|unit|integration|agentic|docker-inference")


def cleanup_old_reports(logger: ValidationLogger):
    """Remove validation reports older than 14 days"""
    report_dir = Path("reports")
    if not report_dir.exists():
        return

    now = datetime.now()
    cutoff = now - timedelta(days=14)
    removed_count = 0

    for report_file in report_dir.glob("backend_validation_report_*.txt"):
        try:
            filename = report_file.name
            timestamp_str = filename.replace("backend_validation_report_", "").replace(".txt", "")
            file_datetime = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")

            if file_datetime < cutoff:
                report_file.unlink()
                removed_count += 1
        except (ValueError, OSError):
            continue

    if removed_count > 0:
        logger.log(f"Report cleanup: Removed {removed_count} reports older than 14 days")


def parse_junit_xml(xml_file: Path) -> tuple[list[tuple[str, str]], str, bool, bool]:
    """Parse JUnit XML file and return (test_results, summary, success, has_skips)"""
    if not xml_file.exists():
        return [], "No XML report generated", False, False

    try:
        tree = ET.parse(xml_file)
        root = tree.getroot()

        test_results = []
        total_tests = 0
        failures = 0
        errors = 0
        skipped = 0

        for testsuite in root:
            for testcase in testsuite:
                total_tests += 1
                test_name = f"{testcase.get('classname', '')}::{testcase.get('name', '')}"

                if testcase.find('failure') is not None:
                    test_results.append(('FAIL', test_name))
                    failures += 1
                elif testcase.find('error') is not None:
                    test_results.append(('ERROR', test_name))
                    errors += 1
                elif testcase.find('skipped') is not None:
                    test_results.append(('SKIP', test_name))
                    skipped += 1
                else:
                    test_results.append(('PASS', test_name))

        summary_parts = []
        if total_tests > 0:
            summary_parts.append(f"{total_tests} tests")
        if failures > 0:
            summary_parts.append(f"{failures} failed")
        if errors > 0:
            summary_parts.append(f"{errors} errors")
        if skipped > 0:
            summary_parts.append(f"{skipped} skipped")

        summary = ", ".join(summary_parts) if summary_parts else "No tests collected"
        success = (failures == 0 and errors == 0)
        has_skips = skipped > 0

        return test_results, summary, success, has_skips

    except Exception as e:
        return [], f"XML parsing error: {e}", False, False


def run_pytest_suite(logger: ValidationLogger, suite_name: str, suite_path: str) -> str:
    """Run pytest on a test suite with per-test visibility"""
    logger.header(f"{suite_name.upper()} Tests")

    dir_path = Path(suite_path)
    if not dir_path.exists():
        logger.log(f"WARN: Directory {suite_path} not found. Skipping.")
        return 'WARN'

    python_exe = resolve_python_executable()
    xml_file = Path(f"test_results_{suite_name}_{datetime.now().strftime('%H%M%S')}.xml")

    try:
        result = subprocess.run(
            [python_exe, "-m", "pytest", suite_path, "--junitxml", str(xml_file), "--tb=short", "-v"],
            cwd=Path.cwd(),
            capture_output=True,
            text=True,
            timeout=300
        )

        test_results, summary, xml_success, has_skips = parse_junit_xml(xml_file)

        # Per-test results
        for status, test_name in test_results:
            status_icon = {'PASS': '✓', 'FAIL': '✗', 'SKIP': '○', 'ERROR': '✗'}.get(status, '?')
            logger.log(f"  {status_icon} {status}: {test_name}")

        # Summary
        if xml_success and result.returncode in [0, 5]:  # 0=Pass, 5=No tests
            if has_skips:
                logger.log(f"PASS WITH SKIPS: {suite_name}: {summary}")
                return 'PASS_WITH_SKIPS'
            else:
                logger.log(f"SUCCESS: {suite_name}: {summary}")
                return 'PASS'
        else:
            logger.log(f"FAILED: {suite_name}: {summary}")
            if result.stderr and not test_results:
                logger.log(result.stderr.strip()[:500])
            return 'FAIL'

    except subprocess.TimeoutExpired:
        logger.log(f"FAILED: {suite_name}: Timeout after 300s")
        return 'FAIL'
    except Exception as e:
        logger.log(f"FAILED: {suite_name}: {e}")
        return 'FAIL'
    finally:
        if xml_file.exists():
            xml_file.unlink()


def run_docker_inference_validation(logger: ValidationLogger) -> str:
    """Validate Docker-based inference pipeline"""
    logger.header("Docker Inference Validation")
    
    steps = [
        ("Compose Config", ["docker", "compose", "config"]),
        ("Build Backend", ["docker", "compose", "build", "backend"]),
        ("Start Redis+Backend", ["docker", "compose", "up", "-d", "redis", "backend"]),
        (
            "Import llama_cpp",
            ["docker", "compose", "exec", "-T", "backend", "python", "-c", "import llama_cpp; print('OK')"]
        ),
    ]

    for step_name, command in steps:
        logger.log(f"Running: {step_name}")
        result = subprocess.run(command, capture_output=True, text=True)
        
        if result.returncode != 0:
            logger.log(f"✗ FAIL: {step_name}")
            stderr_excerpt = (result.stderr or result.stdout or "").strip()[:500]
            logger.log(f"Error: {stderr_excerpt}")
            return 'FAIL'
        
        logger.log(f"✓ PASS: {step_name}")

    # Health check
    logger.log("Checking health endpoint...")
    health_url = "http://localhost:8000/health"
    for attempt in range(20):
        try:
            with urllib.request.urlopen(health_url, timeout=10) as response:
                health_data = response.read().decode("utf-8")
                logger.log(f"✓ PASS: Health check OK")
                break
        except Exception:
            time.sleep(1)
    else:
        logger.log(f"✗ FAIL: Health endpoint unreachable")
        return 'FAIL'

    # Task endpoint
    logger.log("Testing /task endpoint...")
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
            task_payload = response.read().decode("utf-8")
            task_json = json.loads(task_payload)
            llm_output = str(task_json.get("llm_output", ""))
            
            if len(llm_output.strip()) == 0:
                logger.log(f"✗ FAIL: llm_output was empty")
                return 'FAIL'
            
            logger.log(f"✓ PASS: Task returned llm_output: {llm_output[:50]}")
            logger.log(f"SUCCESS: Docker Inference: All checks passed")
            return 'PASS'

    except Exception as exc:
        logger.log(f"✗ FAIL: Task endpoint error: {exc}")
        return 'FAIL'


def main():
    """Main validation function"""
    try:
        selected_suites = parse_scope(sys.argv[1:])
    except ValueError as error:
        print(f"ERROR: {error}")
        return 2

    logger = ValidationLogger()
    cleanup_old_reports(logger)

    # Track results
    results = {}

    for suite_name in selected_suites:
        if suite_name == DOCKER_SCOPE:
            status = run_docker_inference_validation(logger)
        else:
            status = run_pytest_suite(logger, suite_name, SUITES[suite_name])
        
        results[suite_name] = status

    # Summary
    logger.header("Validation Summary")
    for suite_name, status in results.items():
        logger.log(f"{suite_name.upper()}: {status}")
    logger.log("="*60)

    # Machine-readable invariants
    logger.log("\n[INVARIANTS]")
    for suite_name, status in results.items():
        logger.log(f"{suite_name.upper().replace('-', '_')}={status}")

    # Final verdict
    has_any_fail = any(s == 'FAIL' for s in results.values())
    has_any_skips = any(s == 'PASS_WITH_SKIPS' for s in results.values())

    if not has_any_fail:
        if has_any_skips:
            logger.log("\n✅ JARVISv5 backend is VALIDATED WITH EXPECTED SKIPS!")
        else:
            logger.log("\n✅ JARVISv5 backend is validated!")
        exit_code = 0
    else:
        logger.log("\n❌ Validation failed - see specific component failures above")
        exit_code = 1

    logger.save()
    return exit_code


if __name__ == "__main__":
    sys.exit(main())