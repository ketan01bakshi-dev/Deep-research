"""FastAPI wrapper for autonomous Deep Research missions."""

from __future__ import annotations

import io
import os
import uuid
from pathlib import Path
from typing import Any

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

from agent_core import load_agent_env

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
load_agent_env(PROJECT_ROOT)

from apps.api.security import (
    enforce_rate_limit,
    require_api_key,
    validate_prompt,
    validate_topic,
)
from deep_research.autonomous import run_autonomous_mission, run_follow_up_mission
from deep_research.autonomous_mission import mission_from_dict
from deep_research.pipeline import run_pipeline_mission
from deep_research.rag import build_session_corpus, format_corpus_context, query_session_corpus
from deep_research.run_registry import RunRegistry, status_from_result
from deep_research.session_context import (
    RESEARCH_DIR,
    export_session_zip,
    load_session,
    mark_stale_running_sessions,
)
from deep_research.tools.search_support import check_tavily_quota
from deep_research.web.export import export_session_zip_enhanced

app = FastAPI(title="Deep Research API", version="1.2.0")
JOBS_PATH = PROJECT_ROOT / "docs" / "Research" / "jobs.json"
_registry = RunRegistry(persist_path=JOBS_PATH)

# Recover stale sessions on API startup
mark_stale_running_sessions()


class MissionRequest(BaseModel):
    topic: str
    field: str = "general"
    objectives: list[str] = Field(default_factory=list)
    deliverables: list[str] = Field(default_factory=lambda: ["answer"])
    audience: str = "informed lay reader"
    depth: str = "deep"
    scope: str | None = None
    constraints: str | None = None
    success_criteria: list[str] = Field(default_factory=list)
    max_retries: int = 1
    use_pipeline: bool = False
    linked_sessions: list[str] = Field(default_factory=list)
    parent_session_id: str | None = None
    session_id: str | None = None


class FollowUpRequest(BaseModel):
    prompt: str
    deliverables: list[str] = Field(default_factory=lambda: ["answer"])
    max_retries: int = 1


class CorpusQueryRequest(BaseModel):
    question: str
    top_k: int = 5
    rebuild_index: bool = False


def _run_job(run: Any, payload: dict[str, Any]) -> Any:
    mission = mission_from_dict(payload)
    runner = run_pipeline_mission if payload.get("use_pipeline") else run_autonomous_mission
    return runner(
        mission,
        max_completion_retries=payload.get("max_retries", 1),
        linked_sessions=payload.get("linked_sessions") or None,
        parent_session_id=payload.get("parent_session_id"),
        session_id=payload.get("session_id"),
        should_cancel=run.should_cancel,
    )


@app.get("/health")
def health() -> dict[str, Any]:
    checks: dict[str, Any] = {"status": "ok"}
    checks["cursor_api_key"] = bool(os.environ.get("CURSOR_API_KEY", "").strip())
    checks["tavily_api_key"] = bool(os.environ.get("TAVILY_API_KEY", "").strip())
    allowed, remaining = check_tavily_quota()
    checks["tavily_quota_ok"] = allowed
    checks["tavily_remaining"] = remaining
    try:
        RESEARCH_DIR.mkdir(parents=True, exist_ok=True)
        probe = RESEARCH_DIR / ".health_probe"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
        checks["research_dir_writable"] = True
    except OSError as exc:
        checks["research_dir_writable"] = False
        checks["research_dir_error"] = str(exc)
        checks["status"] = "degraded"
    if JOBS_PATH.exists():
        checks["jobs_store_readable"] = True
    else:
        checks["jobs_store_readable"] = True
    if not checks["cursor_api_key"]:
        checks["status"] = "degraded"
    return checks


@app.post("/missions")
def create_mission(
    body: MissionRequest,
    background: BackgroundTasks,
    request: Request,
    _: None = Depends(require_api_key),
) -> dict[str, Any]:
    enforce_rate_limit(request, limit=20)
    validate_topic(body.topic)
    job_id = uuid.uuid4().hex[:12]
    payload = body.model_dump()
    if not payload.get("objectives"):
        payload["objectives"] = [f"Research and synthesize findings on: {body.topic}"]
    run = _registry.create(
        "mission",
        f"Mission: {body.topic[:80]}",
        payload=payload,
        run_id=job_id,
    )

    def _task(active_run: Any) -> Any:
        return _run_job(active_run, payload)

    run.start(_task)
    _registry._persist()
    return {"job_id": job_id, "status": "pending"}


@app.get("/missions/{job_id}")
def get_mission_status(
    job_id: str,
    _: None = Depends(require_api_key),
) -> dict[str, Any]:
    run = _registry.get(job_id)
    if not run:
        raise HTTPException(status_code=404, detail="Job not found")
    snap = run.snapshot()
    if run.result is not None:
        snap["answer"] = getattr(run.result, "answer", None)
        snap["missing_deliverables"] = list(getattr(run.result, "missing_deliverables", []) or [])
        snap["assumptions"] = list(getattr(run.result, "assumptions", []) or [])
    return {"job_id": job_id, **{k: v for k, v in snap.items() if k != "payload"}}


@app.post("/missions/{job_id}/cancel")
def cancel_mission(
    job_id: str,
    _: None = Depends(require_api_key),
) -> dict[str, Any]:
    run = _registry.get(job_id)
    if not run:
        raise HTTPException(status_code=404, detail="Job not found")
    run.request_cancel()
    _registry._persist()
    return {"job_id": job_id, "status": run.snapshot()["status"], "cancel_requested": True}


@app.post("/sessions/{session_id}/follow-up")
def follow_up_session(
    session_id: str,
    body: FollowUpRequest,
    background: BackgroundTasks,
    request: Request,
    _: None = Depends(require_api_key),
) -> dict[str, Any]:
    enforce_rate_limit(request, limit=20)
    validate_prompt(body.prompt)
    job_id = uuid.uuid4().hex[:12]

    def _task(active_run: Any) -> Any:
        return run_follow_up_mission(
            session_id,
            body.prompt,
            body.deliverables,
            max_completion_retries=body.max_retries,
            should_cancel=active_run.should_cancel,
        )

    run = _registry.create(
        "follow_up",
        f"Follow-up: {session_id[:24]}",
        session_id=session_id,
        run_id=job_id,
    )
    run.start(_task)
    _registry._persist()
    return {"job_id": job_id, "status": "pending", "session_id": session_id}


@app.post("/sessions/{session_id}/corpus/query")
def corpus_query(
    session_id: str,
    body: CorpusQueryRequest,
    request: Request,
    _: None = Depends(require_api_key),
) -> dict[str, Any]:
    enforce_rate_limit(request, limit=60)
    try:
        load_session(session_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if body.rebuild_index:
        build_session_corpus(session_id)
    hits = query_session_corpus(session_id, body.question, top_k=body.top_k)
    return {
        "session_id": session_id,
        "question": body.question,
        "hit_count": len(hits),
        "context": format_corpus_context(hits),
        "hits": hits,
    }


@app.get("/sessions/{session_id}")
def get_session(
    session_id: str,
    _: None = Depends(require_api_key),
) -> dict[str, Any]:
    try:
        session = load_session(session_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return session.to_meta()


@app.get("/sessions/{session_id}/export")
def export_session(
    session_id: str,
    request: Request,
    *,
    enhanced: bool = True,
    stream: bool = True,
    _: None = Depends(require_api_key),
):
    enforce_rate_limit(request, limit=10)
    try:
        data = export_session_zip_enhanced(session_id) if enhanced else export_session_zip(session_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    if stream:
        return StreamingResponse(
            io.BytesIO(data),
            media_type="application/zip",
            headers={"Content-Disposition": f'attachment; filename="{session_id}.zip"'},
        )

    import base64

    return JSONResponse(
        {
            "session_id": session_id,
            "zip_base64": base64.b64encode(data).decode("ascii"),
            "enhanced": enhanced,
        }
    )
