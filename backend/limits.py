"""Single-process demo guard: bounded concurrency and a daily paid-run budget."""
import os
import secrets
import threading
import time
from datetime import datetime, timezone
from fastapi import HTTPException, Request

_lock = threading.Lock()
_active = False
_day = ""
_count = 0
_recent = []

def acquire_run(request: Request):
    global _active, _day, _count, _recent
    token = os.getenv("AGENTARENA_API_TOKEN", "")
    if not token:
        raise HTTPException(503, "Live runs are disabled until AGENTARENA_API_TOKEN is configured.")
    if not secrets.compare_digest(request.headers.get("x-arena-token", ""), token):
        raise HTTPException(401, "Invalid investigation access token.")
    with _lock:
        now = time.monotonic()
        today = datetime.now(timezone.utc).date().isoformat()
        if today != _day:
            _day, _count = today, 0
        _recent = [stamp for stamp in _recent if now - stamp < 60]
        if _active:
            raise HTTPException(429, "One investigation is already running. Please try again shortly.")
        if len(_recent) >= int(os.getenv("RUNS_PER_MINUTE", "3")):
            raise HTTPException(429, "Demo request limit reached. Please wait a minute.")
        if _count >= int(os.getenv("DAILY_RUN_LIMIT", "20")):
            raise HTTPException(429, "The live demo's daily run budget has been reached. Recorded evidence is still available.")
        _active = True
        _count += 1
        _recent.append(now)

def release_run():
    global _active
    with _lock:
        _active = False
