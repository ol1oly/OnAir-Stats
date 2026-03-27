"""FastAPI server — NHL Radio Overlay backend."""
from __future__ import annotations

import asyncio
import json
import os
import sys
import time
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles

from transcriber import DeepgramTranscriber

load_dotenv()

# ---------------------------------------------------------------------------
# Shared state
# ---------------------------------------------------------------------------

_ws_clients: set[WebSocket] = set()
_transcriber: DeepgramTranscriber | None = None


# ---------------------------------------------------------------------------
# SERV-04: broadcast helper
# ---------------------------------------------------------------------------

async def broadcast(payload: dict) -> None:
    """Send a JSON payload to all connected /ws clients. Removes dead connections silently."""
    global _ws_clients
    message = json.dumps(payload)
    dead: set[WebSocket] = set()
    for ws in _ws_clients:
        try:
            await ws.send_text(message)
        except Exception:
            dead.add(ws)
    _ws_clients -= dead


def _system_payload(event: str, message: str) -> dict:
    """Build a SystemPayload dict with the current Unix ms timestamp."""
    return {"type": "system", "event": event, "message": message, "ts": int(time.time() * 1000)}


# ---------------------------------------------------------------------------
# on_transcript stub (SERV-05 will replace with extract → stats → broadcast)
# ---------------------------------------------------------------------------

def _on_transcript(text: str, is_final: bool) -> None:
    if is_final:
        print(f"[transcript] {text}", flush=True)


# ---------------------------------------------------------------------------
# SERV-07: transcriber lifecycle callbacks
# ---------------------------------------------------------------------------

def _on_transcriber_ready() -> None:
    asyncio.create_task(broadcast(_system_payload("transcriber_ready", "Deepgram connected")))


def _on_transcriber_error(message: str) -> None:
    asyncio.create_task(broadcast(_system_payload("transcriber_error", message)))


# ---------------------------------------------------------------------------
# Lifespan: start / stop the shared Deepgram transcriber
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    global _transcriber
    api_key = os.environ.get("DEEPGRAM_API_KEY", "")
    if api_key:
        _transcriber = DeepgramTranscriber(
            api_key=api_key,
            on_transcript=_on_transcript,
            on_ready=_on_transcriber_ready,
            on_error=_on_transcriber_error,
        )
        await _transcriber.start()
        print("[server] Deepgram transcriber connected", flush=True)
    else:
        print("[server] DEEPGRAM_API_KEY not set — transcriber disabled", file=sys.stderr, flush=True)
    yield
    if _transcriber is not None:
        await _transcriber.stop()
        print("[server] Deepgram transcriber stopped", flush=True)


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(lifespan=lifespan)


# ---------------------------------------------------------------------------
# SERV-02: WS /audio — receive browser audio blobs, forward to Deepgram
# ---------------------------------------------------------------------------

@app.websocket("/audio")
async def audio_endpoint(websocket: WebSocket) -> None:
    await websocket.accept()
    try:
        while True:
            blob = await websocket.receive_bytes()
            if _transcriber is not None:
                await _transcriber.send_audio(blob)
    except WebSocketDisconnect:
        pass


# ---------------------------------------------------------------------------
# SERV-03: WS /ws — overlay clients receive broadcasted stat payloads
# ---------------------------------------------------------------------------

@app.websocket("/ws")
async def overlay_ws(websocket: WebSocket) -> None:
    await websocket.accept()
    _ws_clients.add(websocket)
    await websocket.send_text(json.dumps(_system_payload("connected", "Overlay connected")))
    try:
        while True:
            await websocket.receive_text()  # keep-alive; client messages are ignored
    except WebSocketDisconnect:
        pass
    finally:
        _ws_clients.discard(websocket)
        await broadcast(_system_payload("disconnected", "Overlay disconnected"))


# ---------------------------------------------------------------------------
# SERV-01: GET / — serve pre-built React frontend
# Mounted last so WebSocket routes take priority.
# ---------------------------------------------------------------------------

FRONTEND_DIST = Path(__file__).parent.parent / "frontend" / "dist"
app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="static")
