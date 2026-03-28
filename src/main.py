import json
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.config import settings
from src.models.review_request import ReviewRequest
from src.models.review_report import ReviewReport
from src.graph.builder import build_review_graph
from src.tools.schema_checker import load_schema
from src.telemetry.tracing import init_telemetry


_graph = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _graph
    init_telemetry()
    _graph = build_review_graph()
    yield


app = FastAPI(
    title="SQL Review Agent",
    description="Multi-Agent Inner Loop DevOps for SQL Server",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request.state.request_id = str(uuid.uuid4())
    response = await call_next(request)
    response.headers["X-Request-ID"] = request.state.request_id
    return response


@app.get("/health")
async def health():
    return {"status": "healthy"}


@app.post("/review", response_model=ReviewReport)
async def review(req: ReviewRequest):
    schema_ctx = req.schema_context
    if schema_ctx is None:
        schema_ctx = load_schema()

    initial_state = {
        "sql_input": req.sql,
        "schema_context": schema_ctx,
        "max_iterations": req.max_iterations,
        "iteration": 0,
        "changelog_entries": [],
    }

    result = _graph.invoke(initial_state)
    report = result["final_report"]

    return ReviewReport(
        status=report["status"],
        iterations=report["iterations"],
        findings=report["findings"],
        cleaned_sql=report["cleaned_sql"],
        documentation=report["documentation"],
        changelog=report["changelog"] if isinstance(report["changelog"], list) else [report["changelog"]],
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"error": str(exc), "request_id": getattr(request.state, "request_id", "unknown")},
    )
