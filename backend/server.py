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
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Literal

from extractor import Extractor
from stats import (
    StatsClient,
    build_goalie_payload,
    build_player_payload,
    build_team_payload,
)
from transcriber import DeepgramTranscriber

load_dotenv()

# ---------------------------------------------------------------------------
# Shared state
# ---------------------------------------------------------------------------

_ws_clients: set[WebSocket] = set()
_transcriber: DeepgramTranscriber | None = None
_extractor = Extractor()
_stats_client = StatsClient()


# ---------------------------------------------------------------------------
# SERV-04: broadcast helper
# ---------------------------------------------------------------------------

async def broadcast(payload: dict) -> None:
    """Wrap payload in the v1 envelope and send to all /ws clients. Removes dead connections silently."""
    global _ws_clients
    message = json.dumps({"v": 1, "payload": payload})
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
# SERV-05: transcript → extract → stats → broadcast pipeline
# ---------------------------------------------------------------------------

async def _fetch_and_broadcast_player(player_id: int, name: str) -> None:
    extracted = await _stats_client.get_player(player_id, name)
    if extracted is None:
        return
    payload = build_goalie_payload(extracted) if extracted["_type"] == "goalie" else build_player_payload(extracted)
    await broadcast(payload)


async def _fetch_and_broadcast_team(abbrev: str) -> None:
    extracted = await _stats_client.get_team(abbrev)
    if extracted is None:
        return
    await broadcast(build_team_payload(extracted))


async def _handle_transcript(text: str) -> None:
    result = await _extractor.extract_entities(text)
    coros = []
    for name in result["players"]:
        player_id = _stats_client.lookup_player_id(name)
        if player_id is not None:
            coros.append(_fetch_and_broadcast_player(player_id, name))
    for abbrev in result["teams"]:
        coros.append(_fetch_and_broadcast_team(abbrev))
    if coros:
        await asyncio.gather(*coros)


def _on_transcript(text: str, is_final: bool) -> None:
    if is_final:
        print(f"[transcript] {text}", flush=True)
        asyncio.create_task(_handle_transcript(text))


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
    await websocket.send_text(json.dumps({"v": 1, "payload": _system_payload("connected", "Overlay connected")}))
    try:
        while True:
            await websocket.receive_text()  # keep-alive; client messages are ignored
    except WebSocketDisconnect:
        pass
    finally:
        _ws_clients.discard(websocket)
        await broadcast(_system_payload("disconnected", "Overlay disconnected"))


# ---------------------------------------------------------------------------
# SERV-08: POST /debug/inject — manually broadcast a stat payload for testing
# ---------------------------------------------------------------------------

class InjectRequest(BaseModel):
    type: Literal["player", "team"]
    id: int | None = None      # NHL player ID (player only)
    name: str | None = None    # canonical name; resolved via lookup if id not given
    abbrev: str | None = None  # team abbreviation (team only)


@app.post("/debug/inject")
async def debug_inject(req: InjectRequest) -> dict:
    """Fetch live stats for the specified entity and broadcast to all /ws clients."""
    if req.type == "player":
        if req.id is not None:
            player_id = req.id
            display_name = str(player_id)
        elif req.name is not None:
            player_id = _stats_client.lookup_player_id(req.name)
            if player_id is None:
                raise HTTPException(status_code=404, detail=f"Player not found: {req.name}")
            display_name = req.name
        else:
            raise HTTPException(status_code=422, detail="Provide 'id' or 'name' for type 'player'")
        await _fetch_and_broadcast_player(player_id, display_name)

    else:  # team
        if req.abbrev is not None:
            abbrev = req.abbrev
        elif req.name is not None:
            abbrev = _stats_client.lookup_team_abbrev(req.name)
            if abbrev is None:
                raise HTTPException(status_code=404, detail=f"Team not found: {req.name}")
        else:
            raise HTTPException(status_code=422, detail="Provide 'abbrev' or 'name' for type 'team'")
        await _fetch_and_broadcast_team(abbrev)

    return {"ok": True}


# ---------------------------------------------------------------------------
# SERV-01: GET / — serve pre-built React frontend
# Mounted last so WebSocket routes take priority.
# ---------------------------------------------------------------------------

FRONTEND_DIST = Path(__file__).parent.parent / "frontend" / "dist"
app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="static")
