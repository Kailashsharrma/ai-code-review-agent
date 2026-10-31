import json
import os
import re
import sys
import time

from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

client = genai.Client(
    api_key=os.environ["GEMINI_API_KEY"],
    http_options=types.HttpOptions(timeout=60000),
)

# Fast lite model. Alternatives: "gemini-3.1-flash-lite", "gemini-flash-lite-latest"
MODEL = "gemini-3.5-flash-lite"

REVIEW_PROMPT = """You are a code reviewer. Input: Python code with line numbers and static analysis findings.
Report only real bugs, security issues and logic errors. Skip style and naming issues.
Severity rules: high = wrong results, crashes or security vulnerabilities; medium = edge cases or weak validation; low = minor issues.
Return ONLY a JSON array, max 12 items, no extra text. Each item:
{"line": int, "severity": "high|medium|low", "category": "bug|security|performance",
 "issue": "short title", "explanation": "one sentence",
 "fixed_code": "the corrected version of the buggy line (or the few lines that need to change), code only, keep original indentation"}
Keep every field brief."""

FIX_PROMPT = """You are a code fixer. You get Python code and a JSON list of issues found in it.
Return ONLY the complete corrected Python code. No markdown fences, no explanation.
Fix only the listed issues and keep everything else unchanged. Keep the code runnable."""


def _generate(prompt, system, json_mode, max_tokens):
    """Call Gemini. Returns (text, error)."""
    use_thinking_setting = True
    for attempt in range(3):
        kwargs = dict(system_instruction=system, max_output_tokens=max_tokens)
        if json_mode:
            kwargs["response_mime_type"] = "application/json"
        if use_thinking_setting:
            kwargs["thinking_config"] = types.ThinkingConfig(thinking_budget=0)
        try:
            response = client.models.generate_content(
                model=MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(**kwargs),
            )
            return (response.text or ""), None
        except Exception as e:
            msg = str(e)
            # Some models reject the thinking setting (400): retry without it
            if use_thinking_setting and ("400" in msg or "INVALID_ARGUMENT" in msg):
                use_thinking_setting = False
                continue
            # Rate limit / overload: wait briefly and retry
            if attempt < 2 and ("429" in msg or "503" in msg):
                time.sleep(5)
                continue
            return "", msg
    return "", "Unknown error"


def _strip_fences(text):
    return re.sub(r"^```(?:json|python)?|```$", "", text.strip(), flags=re.MULTILINE).strip()


def review_code(code: str, static_issues: list) -> list:
    numbered = "\n".join(f"{i}: {l}" for i, l in enumerate(code.splitlines(), 1))
    prompt = (
        f"CODE:\n{numbered}\n\n"
        f"STATIC ANALYSIS FINDINGS:\n{json.dumps(static_issues)}"
    )
    text, error = _generate(prompt, REVIEW_PROMPT, json_mode=True, max_tokens=3500)
    if error:
        return [{"error": error}]
    try:
        return json.loads(_strip_fences(text))
    except json.JSONDecodeError:
        return [{"error": "Invalid or incomplete JSON from model", "raw": text}]


def fix_code(code: str, issues: list) -> str:
    """Return the full corrected code (or an error message starting with 'ERROR:')."""
    prompt = f"CODE:\n{code}\n\nISSUES:\n{json.dumps(issues)}"
    text, error = _generate(prompt, FIX_PROMPT, json_mode=False, max_tokens=6000)
    if error:
        return f"ERROR: {error}"
    return _strip_fences(text)


if __name__ == "__main__":
    from static_analysis import analyze_code

    src = open(sys.argv[1], encoding="utf-8").read()
    start = time.time()
    print(json.dumps(review_code(src, analyze_code(src)), indent=2))
    print(f"\nTotal time: {time.time() - start:.1f}s")