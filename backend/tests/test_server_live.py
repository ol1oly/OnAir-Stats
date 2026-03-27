"""
Live server tests — require DEEPGRAM_API_KEY set in .env.

Tests the real Deepgram WebSocket connection and the WS system-event pipeline.
No mocking — everything hits actual endpoints.

Run from repo root:
    python backend/tests/test_server_live.py

Why no pytest?  Connecting to Deepgram takes 1-5 s per call.  The standalone
runner makes timing visible and keeps the regular pytest suite fast.
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

# Allow importing backend modules directly
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv()

from transcriber import DeepgramTranscriber

# ---------------------------------------------------------------------------
# Pre-flight: need a real key
# ---------------------------------------------------------------------------

api_key = os.environ.get("DEEPGRAM_API_KEY", "")
if not api_key:
    print("ERROR: DEEPGRAM_API_KEY not set in .env — live tests require a real key.")
    sys.exit(1)


# ---------------------------------------------------------------------------
# Result container + helpers  (same pattern as test_stats_live.py)
# ---------------------------------------------------------------------------

@dataclass
class Result:
    name:    str
    ok:      bool  = True
    elapsed: float = 0.0
    error:   str   = ""
    notes:   list[str] = field(default_factory=list)


def _check(r: Result, condition: bool, msg: str) -> None:
    if not condition:
        r.ok = False
        r.notes.append(f"FAIL  {msg}")
    else:
        r.notes.append(f"pass  {msg}")


async def _timed(coro) -> tuple:
    t0 = time.perf_counter()
    value = await coro
    return value, time.perf_counter() - t0


# ---------------------------------------------------------------------------
# Test 1: real key → on_ready fires
# ---------------------------------------------------------------------------

async def test_transcriber_on_ready() -> Result:
    """DeepgramTranscriber.start() with a real key: on_ready fires and WS opens."""
    r = Result(name="transcriber  on_ready (real key)")

    ready_event = asyncio.Event()
    error_msg: list[str] = []  # list so nonlocal isn't needed

    def on_ready() -> None:
        ready_event.set()

    def on_error(msg: str) -> None:
        error_msg.append(msg)

    transcriber = DeepgramTranscriber(
        api_key=api_key,
        on_transcript=lambda text, is_final: None,
        on_ready=on_ready,
        on_error=on_error,
    )

    t0 = time.perf_counter()
    try:
        # start() blocks until _ready is set (which happens right before on_ready fires)
        await asyncio.wait_for(transcriber.start(), timeout=15.0)
        r.elapsed = time.perf_counter() - t0

        _check(r, ready_event.is_set(), "on_ready callback fired")
        _check(r, not error_msg,        "no on_error callback fired")
        _check(r, r.elapsed < 10.0,    f"connected in {r.elapsed * 1000:.0f}ms (< 10 s)")
    except asyncio.TimeoutError:
        r.elapsed = time.perf_counter() - t0
        r.ok    = False
        detail  = f" — on_error said: {error_msg[0]}" if error_msg else ""
        r.error = f"timed out after 15 s{detail}"
    finally:
        await transcriber.stop()

    return r


# ---------------------------------------------------------------------------
# Test 2: bad key → on_error fires (with a short timeout to avoid hanging)
# ---------------------------------------------------------------------------

async def test_transcriber_on_error() -> Result:
    """DeepgramTranscriber with a deliberately bad key: on_error fires."""
    r = Result(name="transcriber  on_error (bad key)")

    error_msg: list[str] = []

    def on_error(msg: str) -> None:
        error_msg.append(msg)

    transcriber = DeepgramTranscriber(
        api_key="bad-key-intentional",
        on_transcript=lambda text, is_final: None,
        on_error=on_error,
    )

    # start() will never unblock (Deepgram rejects → _ready is never set).
    # We use a short timeout and look for on_error having fired.
    t0 = time.perf_counter()
    try:
        await asyncio.wait_for(transcriber.start(), timeout=10.0)
        # If we somehow get here, Deepgram accepted the bad key — unexpected.
        r.ok    = False
        r.error = "start() succeeded with a bad key (unexpected)"
    except asyncio.TimeoutError:
        r.elapsed = time.perf_counter() - t0
        # on_error should have been called before the timeout
        _check(r, bool(error_msg),  "on_error callback fired before timeout")
        if error_msg:
            _check(r, len(error_msg[0]) > 0, f"error message is non-empty: \"{error_msg[0][:80]}\"")
    finally:
        await transcriber.stop()

    return r


# ---------------------------------------------------------------------------
# Test 3: full server — WS /ws sends system:connected with real Deepgram running
# ---------------------------------------------------------------------------

def test_ws_connected_event() -> Result:
    """Full server (real transcriber) — connecting to /ws returns system:connected."""
    r = Result(name="server WS    system:connected (real server)")

    # Bootstrap frontend/dist so StaticFiles doesn't raise at mount time
    dist = Path(__file__).parent.parent.parent / "frontend" / "dist"
    dist.mkdir(parents=True, exist_ok=True)
    idx = dist / "index.html"
    if not idx.exists():
        idx.write_text("<!DOCTYPE html><html><body>test</body></html>", encoding="utf-8")

    # Import here (after sys.path is set) to avoid circular issues at module level
    from fastapi.testclient import TestClient
    import server  # noqa: PLC0415

    t0 = time.perf_counter()
    try:
        with TestClient(server.app) as client:
            with client.websocket_connect("/ws") as ws:
                msg = ws.receive_json()

        r.elapsed = time.perf_counter() - t0
        _check(r, msg.get("type")    == "system",            "type == 'system'")
        _check(r, msg.get("event")   == "connected",         "event == 'connected'")
        _check(r, msg.get("message") == "Overlay connected", "message == 'Overlay connected'")
        _check(r, isinstance(msg.get("ts"), int),            "ts is an int (Unix ms)")

        ts = msg.get("ts", 0)
        now_ms = int(time.time() * 1000)
        _check(r, abs(now_ms - ts) < 30_000, f"ts is recent (within 30 s): {ts}")
    except Exception as exc:
        r.elapsed = time.perf_counter() - t0
        r.ok    = False
        r.error = str(exc)

    return r


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

async def _run_async() -> list[Result]:
    results: list[Result] = []
    results.append(await test_transcriber_on_ready())
    results.append(await test_transcriber_on_error())
    return results


def _print_results(all_results: list[Result]) -> int:
    col_w = max(len(r.name) for r in all_results) + 2
    sep   = "-" * (col_w + 52)

    print(f"\n{sep}")
    print(f"  {'Test':<{col_w}}  {'Status':<8}  {'Time':>9}  Notes")
    print(sep)

    failed = 0
    for r in all_results:
        status   = "PASS" if r.ok else "FAIL"
        time_str = f"{r.elapsed * 1000:>8.1f}ms"
        print(f"  {r.name:<{col_w}}  {status:<8}  {time_str}", end="")

        if r.error:
            print(f"  => {r.error}")
        elif not r.ok:
            print()
            for note in r.notes:
                if note.startswith("FAIL"):
                    print(f"    {note}")
        else:
            print()

        if not r.ok:
            failed += 1

    print(sep)
    passed = len(all_results) - failed
    suffix = "  —  all good" if not failed else f"  —  {failed} FAILED"
    print(f"  {passed}/{len(all_results)} passed{suffix}")
    print(sep)
    return failed


if __name__ == "__main__":
    print("Server live tests — real Deepgram API key…")
    print("(test 2 intentionally uses a bad key; expect a ~10 s wait)\n")

    async_results = asyncio.run(_run_async())
    sync_result   = test_ws_connected_event()   # sync — uses TestClient

    all_results = async_results + [sync_result]
    failed = _print_results(all_results)
    sys.exit(1 if failed else 0)
