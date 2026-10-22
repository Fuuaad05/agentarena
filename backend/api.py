import asyncio
import json
import logging
import os
import queue
import threading

from typing import Literal

from dotenv import load_dotenv

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from pydantic import BaseModel, Field

from backend.pipeline import AgentArenaPipeline
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
    allow_headers=["Content-Type"],
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


# ==========================================
# HELPERS
# ==========================================

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
):
    """
    Execute an investigation inside a temporary workspace.
    """

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
    return {
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
async def investigate(request: InvestigationRequest):

    scenario = resolve_scenario(
        request.scenario_id
    )

    try:
        result = await asyncio.to_thread(
            run_pipeline,
            scenario,
            request.bug_report,
            request.mode,
            request.enable_research,
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


# ==========================================
# STREAMING INVESTIGATION
# ==========================================

@app.post("/api/investigate/stream")
async def investigate_stream(request: InvestigationRequest):

    scenario = resolve_scenario(
        request.scenario_id
    )

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
                event_queue.put(None)

        thread = threading.Thread(
            target=worker,
            daemon=True,
        )

        thread.start()

        while True:

            event = event_queue.get()

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