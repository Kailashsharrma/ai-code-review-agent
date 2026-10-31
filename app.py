import html
import json
import time

import streamlit as st

from analyzer.llm_review import fix_code, review_code
from analyzer.static_analysis import analyze_code

st.set_page_config(page_title="AI Code Review Agent", layout="wide")
st.title("AI Code Review & Bug Detection Agent")
st.caption("Static analysis (pylint + bandit) combined with LLM review. Python only for now.")


def render_marked_code(code, bad_lines):
    """Show the full code with line numbers; buggy lines are highlighted in red."""
    rows = []
    for n, line in enumerate(code.splitlines(), 1):
        text = html.escape(line) or " "
        if n in bad_lines:
            style = "background:rgba(255,75,75,0.25);border-left:3px solid #ff4b4b;"
        else:
            style = "border-left:3px solid transparent;"
        rows.append(f'<div style="{style}padding:0 8px;white-space:pre;">{n:>3}   {text}</div>')
    st.markdown(
        '<div style="font-family:monospace;font-size:13px;overflow-x:auto;'
        'background:#1e1e1e;border-radius:6px;padding:8px 0;">' + "".join(rows) + "</div>",
        unsafe_allow_html=True,
    )


def to_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


uploaded = st.file_uploader("Upload a Python file", type=["py"])
default_code = uploaded.read().decode("utf-8") if uploaded else ""
code = st.text_area("Or paste your code here", value=default_code, height=300)
use_llm = st.checkbox("Also run LLM review (Gemini)", value=True)

if st.button("Analyze", type="primary"):
    if not code.strip():
        st.warning("Please paste or upload some code first.")
        st.stop()

    t0 = time.time()
    with st.spinner("Running static analysis..."):
        static_issues = analyze_code(code)
    static_time = time.time() - t0

    llm_issues = []
    t1 = time.time()
    if use_llm:
        with st.spinner("Running LLM review..."):
            llm_issues = review_code(code, static_issues)
    llm_time = time.time() - t1

    st.session_state["result"] = {
        "code": code,
        "static": static_issues,
        "errors": [i for i in llm_issues if "error" in i],
        "llm": [i for i in llm_issues if "error" not in i],
        "static_time": static_time,
        "llm_time": llm_time,
        "fixed": None,
    }

result = st.session_state.get("result")

if result:
    code_src = result["code"]
    code_lines = code_src.splitlines()
    static_issues = result["static"]
    llm_issues = result["llm"]

    st.caption(f"Static analysis: {result['static_time']:.1f}s | LLM review: {result['llm_time']:.1f}s")

    col1, col2, col3 = st.columns(3)
    col1.metric("Static findings", len(static_issues))
    col2.metric("LLM findings", len(llm_issues))
    col3.metric("High severity", sum(1 for i in llm_issues if i.get("severity") == "high"))

    if result["errors"]:
        st.error(f"LLM error: {result['errors'][0]['error']}")

    if llm_issues:
        bad_lines = {to_int(i.get("line")) for i in llm_issues}

        st.subheader("Your code (wrong lines highlighted)")
        render_marked_code(code_src, bad_lines)

        st.subheader("AI review: what is wrong and how to fix it")
        order = {"high": 0, "medium": 1, "low": 2}
        for i in sorted(llm_issues, key=lambda x: order.get(x.get("severity"), 3)):
            icon = {"high": "🔴", "medium": "🟠", "low": "🟡"}.get(i.get("severity"), "⚪")
            line_no = to_int(i.get("line"))
            original = code_lines[line_no - 1] if line_no and 1 <= line_no <= len(code_lines) else ""
            with st.expander(f"{icon} Line {i.get('line')}: {i.get('issue')}"):
                st.write(f"**Category:** {i.get('category')}  |  **Severity:** {i.get('severity')}")
                st.write(i.get("explanation"))
                left, right = st.columns(2)
                left.markdown("**❌ Wrong (your code)**")
                left.code(original, language="python")
                right.markdown("**✅ Correct**")
                right.code(i.get("fixed_code", ""), language="python")

        st.subheader("Fully corrected code")
        if st.button("Generate fully corrected code"):
            with st.spinner("Generating corrected code..."):
                result["fixed"] = fix_code(code_src, llm_issues)
        if result["fixed"]:
            if result["fixed"].startswith("ERROR:"):
                st.error(result["fixed"])
            else:
                st.code(result["fixed"], language="python")
                st.download_button("Download corrected code", result["fixed"], file_name="fixed_code.py")
                st.caption("Always review the generated code before using it.")

    st.subheader("Static analysis (pylint + bandit)")
    if static_issues:
        rows = ["| Tool | Line | Severity | Code | Message |", "|---|---|---|---|---|"]
        for s in sorted(static_issues, key=lambda x: x["line"]):
            msg = s["message"].replace("|", "/")
            rows.append(f"| {s['tool']} | {s['line']} | {s['severity']} | {s['code']} | {msg} |")
        st.markdown("\n".join(rows))
    else:
        st.success("Static tools found no issues.")

    report = {"static": static_issues, "llm": llm_issues}
    st.download_button(
        "Download report (JSON)",
        json.dumps(report, indent=2),
        file_name="review_report.json",
        mime="application/json",
    )