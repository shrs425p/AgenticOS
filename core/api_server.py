"""HTTP/WebSocket API server for AgenticOs.

Provides a REST + WebSocket interface so AgenticOs can be triggered
programmatically, integrated into CI/CD pipelines, or operated from a
browser-based UI.

Endpoints:
  POST /task          — submit a task, returns {"task_id": "...", "status": "queued"}
  GET  /task/{id}     — poll result; streams SSE events while running
  GET  /tools         — list all registered tools
  GET  /memory        — return MEMORY.md contents
  WS   /stream        — real-time stream of agent events

Security:
  All requests must include header ``X-API-Key: <AGENTICOS_API_KEY>`` (from
  .env).  If the env var is unset, authentication is skipped (dev mode).

Launch::

    python main.py --api --port 8080

Dependencies (optional, graceful ImportError):
    fastapi, uvicorn, starlette
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)

_TASK_STORE: Dict[str, Dict[str, Any]] = {}
_LOCK = threading.Lock()


def _now_iso() -> str:
    return datetime.now().isoformat(sep="T", timespec="seconds")


def _get_api_key() -> str:
    return os.environ.get("AGENTICOS_API_KEY", "").strip()


def _check_api_key(request_key: str) -> bool:
    expected = _get_api_key()
    if not expected:
        return True  # dev mode: no auth
    return request_key == expected


# ---------------------------------------------------------------------------
# FastAPI application factory
# ---------------------------------------------------------------------------


def create_app(
    run_callback: Optional[Callable[[str], str]] = None,
    tools_callback: Optional[Callable[[], Dict[str, Any]]] = None,
    workspace: str = "workspace",
):
    """Build and return the FastAPI application.

    Args:
        run_callback: ``(task_description) -> final_answer`` executed in a
                      background thread for each submitted task.
        tools_callback: Returns the tool registry dict for ``GET /tools``.
        workspace: Agent workspace path (used to serve MEMORY.md).
    """
    try:
        from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Request
        from fastapi.responses import JSONResponse, StreamingResponse
        from pydantic import BaseModel
    except ImportError as exc:
        raise ImportError(
            "fastapi and uvicorn are required for API mode. "
            "Install them with: pip install fastapi uvicorn"
        ) from exc

    app = FastAPI(
        title="AgenticOs API",
        description="Programmatic interface for the AgenticOs autonomous framework.",
        version="2.1",
    )

    # -------- Auth middleware --------

    def _require_auth(request: Request):
        key = request.headers.get("X-API-Key", "")
        if not _check_api_key(key):
            raise HTTPException(status_code=401, detail="Invalid or missing API key.")

    # -------- Models --------

    class TaskRequest(BaseModel):
        task: str

    # -------- POST /task --------

    @app.post("/task")
    async def submit_task(body: TaskRequest, request: Request):
        _require_auth(request)
        task_id = str(uuid.uuid4())
        with _LOCK:
            _TASK_STORE[task_id] = {
                "task_id": task_id,
                "task": body.task,
                "status": "queued",
                "result": None,
                "events": [],
                "created_at": _now_iso(),
                "updated_at": _now_iso(),
            }

        def _run():
            with _LOCK:
                _TASK_STORE[task_id]["status"] = "running"
                _TASK_STORE[task_id]["updated_at"] = _now_iso()
            try:
                if run_callback:
                    result = run_callback(body.task)
                else:
                    result = f"(no run_callback configured; task: {body.task})"
                with _LOCK:
                    _TASK_STORE[task_id]["status"] = "done"
                    _TASK_STORE[task_id]["result"] = str(result)
                    _TASK_STORE[task_id]["updated_at"] = _now_iso()
                    _TASK_STORE[task_id]["events"].append(
                        {"type": "done", "data": str(result)[:500], "ts": _now_iso()}
                    )
            except Exception as exc:
                logger.error("API task %s failed: %s", task_id, exc)
                with _LOCK:
                    _TASK_STORE[task_id]["status"] = "error"
                    _TASK_STORE[task_id]["result"] = f"ERROR: {exc}"
                    _TASK_STORE[task_id]["updated_at"] = _now_iso()

        t = threading.Thread(target=_run, daemon=True)
        t.start()

        return {"task_id": task_id, "status": "queued"}

    # -------- GET /task/{id} --------

    @app.get("/task/{task_id}")
    async def get_task(task_id: str, request: Request):
        _require_auth(request)
        with _LOCK:
            entry = _TASK_STORE.get(task_id)
        if entry is None:
            raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found.")

        accept = request.headers.get("Accept", "")
        if "text/event-stream" in accept:
            # SSE stream: poll until done
            def _stream():
                last_event_count = 0
                while True:
                    with _LOCK:
                        entry = _TASK_STORE.get(task_id, {})
                    events = entry.get("events", [])[last_event_count:]
                    for ev in events:
                        yield f"data: {json.dumps(ev)}\n\n"
                    last_event_count += len(events)
                    status = entry.get("status", "queued")
                    if status in ("done", "error"):
                        yield f"data: {json.dumps({'type': 'end', 'status': status})}\n\n"
                        break
                    time.sleep(0.5)

            return StreamingResponse(_stream(), media_type="text/event-stream")

        return JSONResponse(content=entry)

    # -------- GET /tools --------

    @app.get("/tools")
    async def list_tools(request: Request):
        _require_auth(request)
        if tools_callback:
            data = tools_callback()
        else:
            data = {}
        return JSONResponse(content={"tools": data})

    # -------- GET /memory --------

    @app.get("/memory")
    async def get_memory(request: Request):
        _require_auth(request)
        memory_path = Path(workspace) / "MEMORY.md"
        if memory_path.exists():
            try:
                content = memory_path.read_text(encoding="utf-8")
            except Exception:
                content = "(unable to read MEMORY.md)"
        else:
            content = "(MEMORY.md not found)"
        return JSONResponse(content={"content": content})

    # -------- WS /stream --------

    _ws_clients: list = []
    _ws_lock = threading.Lock()

    @app.websocket("/stream")
    async def websocket_stream(ws: WebSocket):
        api_key = ws.query_params.get("api_key", "")
        if not _check_api_key(api_key):
            await ws.close(code=1008, reason="Invalid API key")
            return
        await ws.accept()
        with _ws_lock:
            _ws_clients.append(ws)
        try:
            while True:
                data = await ws.receive_text()
                # Echo back as acknowledgement
                await ws.send_text(json.dumps({"echo": data, "ts": _now_iso()}))
        except WebSocketDisconnect:
            pass
        finally:
            with _ws_lock:
                if ws in _ws_clients:
                    _ws_clients.remove(ws)

    # Expose the broadcast helper on the app for external use
    def broadcast(event: Dict[str, Any]):
        """Broadcast an event dict to all connected WebSocket clients."""
        with _ws_lock:
            clients = list(_ws_clients)
        msg = json.dumps(event)
        for ws_client in clients:
            try:
                # Note: this is called from sync threads; use asyncio workaround
                import asyncio

                loop = None
                try:
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                if loop.is_running():
                    asyncio.ensure_future(ws_client.send_text(msg), loop=loop)
                else:
                    loop.run_until_complete(ws_client.send_text(msg))
            except Exception:
                pass

    app.broadcast = broadcast  # type: ignore[attr-defined]
    return app


# ---------------------------------------------------------------------------
# Server runner
# ---------------------------------------------------------------------------


def run_api_server(
    host: str = "0.0.0.0",
    port: int = 8080,
    run_callback: Optional[Callable[[str], str]] = None,
    tools_callback: Optional[Callable[[], Dict[str, Any]]] = None,
    workspace: str = "workspace",
):
    """Start the uvicorn server in the foreground.

    This function blocks until the server is stopped (Ctrl-C).
    """
    try:
        import uvicorn
    except ImportError as exc:
        raise ImportError(
            "uvicorn is required for API mode.  Install: pip install uvicorn"
        ) from exc

    app = create_app(
        run_callback=run_callback,
        tools_callback=tools_callback,
        workspace=workspace,
    )
    logger.info("AgenticOs API server starting on %s:%d", host, port)
    uvicorn.run(app, host=host, port=port, log_level="info")
