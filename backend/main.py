import json
import os
from pathlib import Path
from typing import Any, Dict, List

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from .auth import get_current_user
from .auth import router as auth_router
from .config import settings
from .db import get_stats, init_db, record_attempt, record_conversation
from .levels import (
    build_system_prompt,
    get_levels_public,
    get_secret,
    get_valid_level_ids,
)
from .llm import check_success, health_check, stream_chat

# Validate config on startup
settings.validate()

limiter = Limiter(key_func=get_remote_address)

app = FastAPI(title="Jailbreaking Challenge", docs_url=None, redoc_url=None)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


@app.middleware("http")
async def strip_configured_root_path(request: Request, call_next):
    root_path = request.scope.get("root_path") or ""
    path = request.scope.get("path") or ""

    if root_path and path == root_path:
        request.scope["path"] = "/"
        request.scope["raw_path"] = b"/"
    elif root_path and path.startswith(f"{root_path}/"):
        stripped_path = path[len(root_path) :]
        request.scope["path"] = stripped_path or "/"
        request.scope["raw_path"] = (stripped_path or "/").encode("utf-8")

    return await call_next(request)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production via nginx
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)

# DB init
init_db()

# Mount auth router
app.include_router(auth_router, prefix="/api")


class ChatRequest(BaseModel):
    level: str
    messages: List[Dict[str, Any]]
    prompt: str = Field(..., min_length=1, max_length=1000)


@app.get("/api/health")
async def health():
    online = await health_check()
    return {"online": online, "model": settings.MODEL_NAME}


@app.get("/api/levels")
async def levels():
    return get_levels_public()


@app.post("/api/chat")
@limiter.limit("30/minute")
async def chat(
    request: Request,
    body: ChatRequest,
    _user: str = Depends(get_current_user),
):
    # Validate level
    if body.level not in get_valid_level_ids():
        raise HTTPException(status_code=400, detail="Invalid level")

    # Sanitize: strip leading/trailing whitespace, limit prompt
    prompt = body.prompt.strip()
    if not prompt:
        raise HTTPException(status_code=422, detail="Prompt cannot be empty")

    # Enforce max prompt length (belt-and-suspenders from Pydantic)
    if len(prompt) > 1000:
        raise HTTPException(status_code=422, detail="Prompt too long (max 1000 chars)")

    # Build current messages (append the new prompt from user)
    all_messages = list(body.messages) + [{"role": "user", "content": prompt}]

    system_prompt = build_system_prompt(body.level)
    secret = get_secret(body.level)

    async def event_stream():
        accumulated = ""
        try:
            async for token in stream_chat(system_prompt, all_messages):
                accumulated += token
                data = json.dumps({"delta": token})
                yield f"data: {data}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
            return

        # After full response, detect success
        success = check_success(accumulated, secret)

        # Record attempt (aggregate stats)
        record_attempt(body.level, success, len(prompt))

        # Record full anonymous conversation (never exposed via API)
        full_convo = all_messages + [{"role": "assistant", "content": accumulated}]
        record_conversation(body.level, full_convo, success)

        # Send done event — do NOT include the secret word
        yield f"data: {json.dumps({'done': True, 'success': success})}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )


@app.get("/api/stats")
async def stats(_user: str = Depends(get_current_user)):
    return get_stats()


# Serve frontend static files (if built)
frontend_dist = Path(__file__).parent.parent / "frontend" / "dist"
if frontend_dist.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="static")
