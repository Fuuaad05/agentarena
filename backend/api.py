import asyncio
import json
import logging
import os
import queue
import threading
import subprocess
import shutil

from typing import Literal

from dotenv import load_dotenv

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from pydantic import BaseModel, Field

from backend.pipeline import AgentArenaPipeline
from backend.custom_audit import run_custom_audit, validate_custom_input
from backend.limits import acquire_run, release_run
from backend.workspace import investigation_workspace

from backend.database.storage import (
    list_investigations,
    get_investigation,
)

from backend.scenarios import (
    get_scenario,
    list_scenarios,
)


# ==========================================
# ENVIRONMENT
# ==========================================

load_dotenv()


# ==========================================
# LOGGING
# ==========================================

logger = logging.getLogger("agentarena")


# ==========================================
# FASTAPI APPLICATION
# ==========================================

app = FastAPI(
    title="AgentArena API",
    description="Evidence-based verification for AI coding agents",
    version="1.2.0",
)

allowed_origins = [
    origin.strip().rstrip("/")
    for origin in os.getenv(
        "ALLOWED_ORIGINS",
        "http://localhost:3000,http://127.0.0.1:3000",
    ).split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "X-Arena-Token"],
)


# ==========================================
# REQUEST MODELS
# ==========================================

class InvestigationRequest(BaseModel):

    scenario_id: str = Field(
        default="discount",
        max_length=50,
    )

    bug_report: str = Field(
        min_length=1,
        max_length=3000,
    )

    mode: Literal[
        "repair",
        "audit",
    ] = "repair"

    enable_research: bool = True
    source_code: str | None = Field(default=None, max_length=20000)
    existing_tests: str = Field(default="", max_length=12000)


# ==========================================
# HELPERS
# ==========================================

def resolve_request(request):
    if request.scenario_id != "custom":
        return resolve_scenario(request.scenario_id)
    if os.getenv("ENABLE_CUSTOM_AUDIT", "false").lower() != "true":
        raise HTTPException(503, "Custom audits are disabled on this host.")
    if request.mode != "audit":
        raise HTTPException(400, "Custom code supports audit only.")
    try:
        validate_custom_input(request.source_code, request.existing_tests)
    except (ValueError, SyntaxError) as error:
        raise HTTPException(422, f"Invalid custom input: {error}")
    return None


def resolve_scenario(scenario_id: str):

    try:
        scenario = get_scenario(scenario_id)

    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Unknown scenario",
        )

    if not scenario.repo_path.is_dir():
        raise HTTPException(
            status_code=500,
            detail="Scenario repository not found",
        )

    return scenario


def run_pipeline(
    scenario,
    bug_report: str,
    mode: str = "repair",
    enable_research: bool = True,
    event_callback=None,
    source_code=None,
    existing_tests="",
):
    """
    Execute an investigation inside a temporary workspace.
    """

    if scenario is None:
        return run_custom_audit(source_code, existing_tests, bug_report, event_callback)

    with investigation_workspace(
        str(scenario.repo_path)
    ) as workspace:

        pipeline = AgentArenaPipeline(
            repo_path=str(workspace),
            scenario=scenario,
            event_callback=event_callback,
            enable_research=enable_research,
        )

        return pipeline.run(
            bug_report,
            mode=mode,
        )


# ==========================================
# HEALTH
# ==========================================

@app.get("/")
def root():
    return {
        "project": "AgentArena",
        "version": "1.2",
        "status": "running",
    }


@app.get("/api/health")
def health():
    docker_ready = False
    if shutil.which("docker"):
        try:
            docker_ready = subprocess.run(["docker", "info", "--format", "{{.ServerVersion}}"], capture_output=True, timeout=15).returncode == 0
        except (OSError, subprocess.TimeoutExpired):
            pass
    model_ready = bool(os.getenv("NEBIUS_API_KEY") and os.getenv("NEBIUS_BASE_URL"))
    return {
        "ready": docker_ready and model_ready and bool(os.getenv("AGENTARENA_API_TOKEN")),
        "dependencies": {"docker_daemon": docker_ready, "model_configured": model_ready, "tavily_configured": bool(os.getenv("TAVILY_API_KEY"))},
        "features": {"custom_audit": os.getenv("ENABLE_CUSTOM_AUDIT", "false").lower() == "true"},
        "status": "healthy",
        "ai_provider": "Nebius Token Factory",
        "model_family": "NVIDIA Nemotron",
        "sandbox": "Docker",
    }


# ==========================================
# SCENARIOS
# ==========================================

@app.get("/api/scenarios")
def scenarios():
    return {
        "scenarios": list_scenarios()
    }


# ==========================================
# STANDARD INVESTIGATION
# ==========================================

@app.post("/api/investigate")
async def investigate(request: InvestigationRequest, http_request: Request):

    scenario = resolve_request(request)

    acquire_run(http_request)
    try:
        result = await asyncio.to_thread(
            run_pipeline,
            scenario,
            request.bug_report,
            request.mode,
            request.enable_research,
            source_code=request.source_code,
            existing_tests=request.existing_tests,
        )

        return result

    except Exception:
        logger.exception(
            "Investigation failed"
        )

        raise HTTPException(
            status_code=500,
            detail="Investigation failed",
        )
    finally:
        release_run()


# ==========================================
# STREAMING INVESTIGATION
# ==========================================

@app.post("/api/investigate/stream")
async def investigate_stream(request: InvestigationRequest, http_request: Request):

    scenario = resolve_request(request)

    # Reject unauthorised/over-budget requests before returning streaming headers.
    acquire_run(http_request)
    def event_generator():

        event_queue = queue.Queue()

        def callback(event):

            event_queue.put({
                "type": "progress",
                "data": event,
            })

        def worker():

            try:
                report = run_pipeline(
                    scenario=scenario,
                    bug_report=request.bug_report,
                    mode=request.mode,
                    enable_research=request.enable_research,
                    event_callback=callback,
                    source_code=request.source_code,
                    existing_tests=request.existing_tests,
                )

                event_queue.put({
                    "type": "complete",
                    "data": report,
                })

            except Exception:

                logger.exception(
                    "Streaming investigation failed"
                )

                event_queue.put({
                    "type": "error",
                    "data": {
                        "message": "Investigation failed",
                    },
                })

            finally:
                release_run()
                event_queue.put(None)

        thread = threading.Thread(
            target=worker,
            daemon=True,
        )

        try:
            thread.start()
        except Exception:
            release_run()
            raise

        while True:

            try:
                event = event_queue.get(timeout=15)
            except queue.Empty:
                yield ": heartbeat\n\n"
                continue

            if event is None:
                break

            yield (
                "data: "
                + json.dumps(event)
                + "\n\n"
            )

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


# ==========================================
# INVESTIGATION HISTORY
# ==========================================

@app.get("/api/investigations")
def investigation_history():

    return {
        "investigations": list_investigations()
    }


@app.get("/api/investigations/{investigation_id}")
def investigation_details(
    investigation_id: int,
):

    report = get_investigation(
        investigation_id
    )

    if report is None:

        raise HTTPException(
            status_code=404,
            detail="Investigation not found",
        )

    return report