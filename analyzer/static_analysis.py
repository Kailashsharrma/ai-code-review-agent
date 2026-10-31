import json
import os
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor


def run_pylint(file_path):
    result = subprocess.run(
        [sys.executable, "-m", "pylint", file_path,
         "--output-format=json", "--disable=C,R", "--persistent=n"],
        capture_output=True, text=True
    )
    try:
        issues = json.loads(result.stdout) if result.stdout.strip() else []
    except json.JSONDecodeError:
        issues = []
    return [
        {
            "tool": "pylint",
            "line": i["line"],
            "severity": i["type"],
            "code": i["message-id"],
            "message": i["message"],
        }
        for i in issues
    ]


def run_bandit(file_path):
    result = subprocess.run(
        [sys.executable, "-m", "bandit", "-f", "json", "-q", file_path],
        capture_output=True, text=True
    )
    try:
        data = json.loads(result.stdout) if result.stdout.strip() else {}
    except json.JSONDecodeError:
        data = {}
    return [
        {
            "tool": "bandit",
            "line": r["line_number"],
            "severity": r["issue_severity"],
            "code": r["test_id"],
            "message": r["issue_text"],
        }
        for r in data.get("results", [])
    ]


def analyze_code(code: str):
    """Take a Python code string and return a list of static analysis issues."""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".py", delete=False, encoding="utf-8"
    ) as f:
        f.write(code)
        path = f.name
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            pylint_future = pool.submit(run_pylint, path)
            bandit_future = pool.submit(run_bandit, path)
            return pylint_future.result() + bandit_future.result()
    finally:
        os.remove(path)


if __name__ == "__main__":
    sample = open(sys.argv[1], encoding="utf-8").read()
    print(json.dumps(analyze_code(sample), indent=2))