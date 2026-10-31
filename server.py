import time
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from pydantic import BaseModel

from analyzer.llm_review import fix_code, review_code
from analyzer.static_analysis import analyze_code

app = FastAPI(title="AI Code Review Agent")
INDEX = Path(__file__).parent / "static" / "index.html"


class AnalyzeIn(BaseModel):
    code: str
    use_llm: bool = True


class FixIn(BaseModel):
    code: str
    issues: list[dict]


@app.get("/")
def index():
    return FileResponse(INDEX)


@app.post("/api/analyze")
def analyze(body: AnalyzeIn):
    t0 = time.time()
    static = analyze_code(body.code)
    t1 = time.time()
    llm, error = [], None
    if body.use_llm:
        result = review_code(body.code, static)
        errors = [i for i in result if "error" in i]
        error = errors[0]["error"] if errors else None
        llm = [i for i in result if "error" not in i]
    return {
        "static": static,
        "llm": llm,
        "error": error,
        "static_time": round(t1 - t0, 1),
        "llm_time": round(time.time() - t1, 1),
    }


@app.post("/api/fix")
def fix(body: FixIn):
    fixed = fix_code(body.code, body.issues)
    if fixed.startswith("ERROR:"):
        return {"fixed": None, "error": fixed}
    return {"fixed": fixed, "error": None}
