"""
Tests for backend/server.py — SERV-01 through SERV-04.

Run from backend/:
    python -m pytest tests/test_server.py -v
"""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parent.parent))

# ---------------------------------------------------------------------------
# frontend/dist bootstrap
# StaticFiles raises at mount-time if the directory does not exist.
# Create a minimal placeholder so tests work without a full npm build.
# ---------------------------------------------------------------------------
_DIST = Path(__file__).parent.parent.parent / "frontend" / "dist"
_DIST.mkdir(parents=True, exist_ok=True)
_INDEX = _DIST / "index.html"
if not _INDEX.exists():
    _INDEX.write_text(
        "<!DOCTYPE html><html><body>NHL Overlay Test</body></html>",
        encoding="utf-8",
    )

import server  # noqa: E402 — must come after dist bootstrap


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def mock_transcriber(monkeypatch):
    """Inject a fake API key and replace DeepgramTranscriber with an async mock."""
    monkeypatch.setenv("DEEPGRAM_API_KEY", "test-fake-key")
    mock = MagicMock()
    mock.start = AsyncMock()
    mock.stop = AsyncMock()
    mock.send_audio = AsyncMock()
    with patch("server.DeepgramTranscriber", return_value=mock):
        yield mock


@pytest.fixture()
def client(mock_transcriber):
    """TestClient with lifespan enabled (transcriber start/stop runs)."""
    with TestClient(server.app) as c:
        yield c


@pytest.fixture(autouse=True)
def reset_ws_clients():
    """Clear the overlay client set before and after every test."""
    server._ws_clients.clear()
    yield
    server._ws_clients.clear()


@pytest.fixture()
def mock_transcriber_cls(monkeypatch):
    """Returns (class_mock, instance_mock) — lets tests inspect constructor kwargs."""
    monkeypatch.setenv("DEEPGRAM_API_KEY", "test-fake-key")
    instance = MagicMock()
    instance.start = AsyncMock()
    instance.stop = AsyncMock()
    instance.send_audio = AsyncMock()
    with patch("server.DeepgramTranscriber", return_value=instance) as cls_mock:
        yield cls_mock, instance


# ---------------------------------------------------------------------------
# SERV-01 — GET / serves React build
# ---------------------------------------------------------------------------

class TestStaticFileEndpoint:
    def test_returns_200(self, client):
        assert client.get("/").status_code == 200

    def test_content_type_is_html(self, client):
        assert "text/html" in client.get("/").headers["content-type"]

    def test_body_contains_html_tag(self, client):
        assert "<html" in client.get("/").text.lower()


# ---------------------------------------------------------------------------
# SERV-02 — WS /audio forwards blobs to DeepgramTranscriber
# ---------------------------------------------------------------------------

class TestAudioWebSocket:
    def test_accepts_connection(self, client):
        with client.websocket_connect("/audio"):
            pass  # no exception = accepted

    def test_forwards_blob_to_transcriber(self, client, mock_transcriber):
        blob = b"\x00\xff" * 512
        with client.websocket_connect("/audio") as ws:
            ws.send_bytes(blob)
        mock_transcriber.send_audio.assert_called_once_with(blob)

    def test_forwards_multiple_blobs(self, client, mock_transcriber):
        blobs = [b"chunk-a", b"chunk-b", b"chunk-c"]
        with client.websocket_connect("/audio") as ws:
            for b in blobs:
                ws.send_bytes(b)
        assert mock_transcriber.send_audio.call_count == len(blobs)

    def test_no_crash_when_transcriber_is_none(self, client):
        """send_audio must be a no-op when the transcriber was not initialised."""
        saved = server._transcriber
        server._transcriber = None
        try:
            with client.websocket_connect("/audio") as ws:
                ws.send_bytes(b"audio data")
        finally:
            server._transcriber = saved


# ---------------------------------------------------------------------------
# SERV-03 — WS /ws manages overlay clients
# ---------------------------------------------------------------------------

class TestOverlayWebSocket:
    def test_accepts_connection(self, client):
        with client.websocket_connect("/ws"):
            pass

    def test_client_added_while_connected(self, client):
        with client.websocket_connect("/ws"):
            assert len(server._ws_clients) == 1

    def test_client_removed_after_disconnect(self, client):
        with client.websocket_connect("/ws"):
            pass
        assert len(server._ws_clients) == 0

    def test_multiple_clients_tracked(self, client):
        with client.websocket_connect("/ws"):
            with client.websocket_connect("/ws"):
                assert len(server._ws_clients) == 2
        assert len(server._ws_clients) == 0

    def test_client_message_does_not_crash(self, client):
        """The server ignores text from /ws clients without raising."""
        with client.websocket_connect("/ws") as ws:
            ws.send_text("ignored")


# ---------------------------------------------------------------------------
# SERV-04 — broadcast() sends JSON to all /ws clients
# ---------------------------------------------------------------------------

def _mock_ws(fail: bool = False) -> MagicMock:
    ws = MagicMock()
    if fail:
        ws.send_text = AsyncMock(side_effect=RuntimeError("connection lost"))
    else:
        ws.send_text = AsyncMock()
    return ws


class TestBroadcast:
    def test_sends_json_to_all_clients(self):
        ws1, ws2 = _mock_ws(), _mock_ws()
        server._ws_clients = {ws1, ws2}
        payload = {"type": "player", "player": "Connor McDavid", "stats": {}}

        asyncio.run(server.broadcast(payload))

        expected = json.dumps(payload)
        ws1.send_text.assert_called_once_with(expected)
        ws2.send_text.assert_called_once_with(expected)

    def test_removes_dead_client_on_send_failure(self):
        live = _mock_ws()
        dead = _mock_ws(fail=True)
        server._ws_clients = {live, dead}

        asyncio.run(server.broadcast({"type": "team"}))

        assert dead not in server._ws_clients
        assert live in server._ws_clients

    def test_empty_client_set_does_not_raise(self):
        server._ws_clients = set()
        asyncio.run(server.broadcast({"type": "player"}))  # must not raise

    def test_payload_is_serialised_to_valid_json(self):
        ws = _mock_ws()
        server._ws_clients = {ws}
        payload = {"type": "team", "team": "Edmonton Oilers", "abbrev": "EDM"}

        asyncio.run(server.broadcast(payload))

        sent = ws.send_text.call_args[0][0]
        assert json.loads(sent) == payload

    def test_live_clients_still_receive_when_one_dead(self):
        live1, live2, dead = _mock_ws(), _mock_ws(), _mock_ws(fail=True)
        server._ws_clients = {live1, live2, dead}

        asyncio.run(server.broadcast({"type": "player"}))

        live1.send_text.assert_called_once()
        live2.send_text.assert_called_once()


# ---------------------------------------------------------------------------
# SERV-07 — SystemPayload events
# ---------------------------------------------------------------------------

class TestSystemEvents:
    def test_ws_connect_sends_system_connected(self, client):
        with client.websocket_connect("/ws") as ws:
            msg = ws.receive_json()
        assert msg["type"] == "system"
        assert msg["event"] == "connected"
        assert msg["message"] == "Overlay connected"
        assert isinstance(msg["ts"], int)

    def test_ws_connect_ts_is_recent_unix_ms(self, client):
        import time as _time
        before = int(_time.time() * 1000)
        with client.websocket_connect("/ws") as ws:
            msg = ws.receive_json()
        after = int(_time.time() * 1000)
        assert before <= msg["ts"] <= after

    def test_ws_disconnect_broadcasts_disconnected_to_remaining(self, client):
        """After a /ws client disconnects, remaining clients receive system:disconnected."""
        observer = _mock_ws()
        with client.websocket_connect("/ws"):
            server._ws_clients.add(observer)
        # The observer should have received exactly one call: the disconnected broadcast
        observer.send_text.assert_called_once()
        msg = json.loads(observer.send_text.call_args[0][0])
        assert msg["type"] == "system"
        assert msg["event"] == "disconnected"
        assert msg["message"] == "Overlay disconnected"
        assert isinstance(msg["ts"], int)

    def test_transcriber_constructed_with_on_ready(self, mock_transcriber_cls):
        cls_mock, _ = mock_transcriber_cls
        with TestClient(server.app):
            pass
        kwargs = cls_mock.call_args.kwargs
        assert "on_ready" in kwargs
        assert callable(kwargs["on_ready"])

    def test_transcriber_constructed_with_on_error(self, mock_transcriber_cls):
        cls_mock, _ = mock_transcriber_cls
        with TestClient(server.app):
            pass
        kwargs = cls_mock.call_args.kwargs
        assert "on_error" in kwargs
        assert callable(kwargs["on_error"])

    def test_on_ready_broadcasts_transcriber_ready(self, mock_transcriber_cls):
        cls_mock, _ = mock_transcriber_cls
        with TestClient(server.app):
            on_ready = cls_mock.call_args.kwargs["on_ready"]

        recorded: list[dict] = []

        async def fake_broadcast(payload: dict) -> None:
            recorded.append(payload)

        with patch("server.broadcast", side_effect=fake_broadcast):
            async def run() -> None:
                on_ready()
                await asyncio.sleep(0)  # yield so the created task executes

            asyncio.run(run())

        assert len(recorded) == 1
        assert recorded[0]["type"] == "system"
        assert recorded[0]["event"] == "transcriber_ready"
        assert recorded[0]["message"] == "Deepgram connected"
        assert isinstance(recorded[0]["ts"], int)

    def test_on_error_broadcasts_transcriber_error_with_message(self, mock_transcriber_cls):
        cls_mock, _ = mock_transcriber_cls
        with TestClient(server.app):
            on_error = cls_mock.call_args.kwargs["on_error"]

        recorded: list[dict] = []

        async def fake_broadcast(payload: dict) -> None:
            recorded.append(payload)

        with patch("server.broadcast", side_effect=fake_broadcast):
            async def run() -> None:
                on_error("invalid API key")
                await asyncio.sleep(0)

            asyncio.run(run())

        assert len(recorded) == 1
        assert recorded[0]["type"] == "system"
        assert recorded[0]["event"] == "transcriber_error"
        assert recorded[0]["message"] == "invalid API key"
        assert isinstance(recorded[0]["ts"], int)
