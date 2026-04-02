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

        expected = json.dumps({"v": 1, "payload": payload})
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

    def test_wraps_payload_in_v1_envelope(self):
        ws = _mock_ws()
        server._ws_clients = {ws}
        payload = {"type": "team", "team": "Edmonton Oilers", "abbrev": "EDM"}

        asyncio.run(server.broadcast(payload))

        sent = json.loads(ws.send_text.call_args[0][0])
        assert sent == {"v": 1, "payload": payload}

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
            envelope = ws.receive_json()
        assert envelope["v"] == 1
        msg = envelope["payload"]
        assert msg["type"] == "system"
        assert msg["event"] == "connected"
        assert msg["message"] == "Overlay connected"
        assert isinstance(msg["ts"], int)

    def test_ws_connect_ts_is_recent_unix_ms(self, client):
        import time as _time
        before = int(_time.time() * 1000)
        with client.websocket_connect("/ws") as ws:
            envelope = ws.receive_json()
        after = int(_time.time() * 1000)
        assert before <= envelope["payload"]["ts"] <= after

    def test_ws_disconnect_broadcasts_disconnected_to_remaining(self, client):
        """After a /ws client disconnects, remaining clients receive system:disconnected."""
        observer = _mock_ws()
        with client.websocket_connect("/ws"):
            server._ws_clients.add(observer)
        # The observer should have received exactly one call: the disconnected broadcast
        observer.send_text.assert_called_once()
        envelope = json.loads(observer.send_text.call_args[0][0])
        assert envelope["v"] == 1
        msg = envelope["payload"]
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


# ---------------------------------------------------------------------------
# SERV-05/06 — transcript → extract → stats → broadcast pipeline
# ---------------------------------------------------------------------------

_SKATER_EXTRACTED = {
    "_type": "skater",
    "id": 8478402,
    "name": "Connor McDavid",
    "team": "EDM",
    "position": "C",
    "headshot_url": "https://example.com/mcdavid.png",
    "stats": {
        "season": "20242025",
        "games_played": 62,
        "goals": 32,
        "assists": 100,
        "points": 132,
        "plus_minus": 15,
    },
}

_GOALIE_EXTRACTED = {
    "_type": "goalie",
    "id": 8474593,
    "name": "Jacob Markstrom",
    "team": "NJD",
    "position": "G",
    "headshot_url": "https://example.com/markstrom.png",
    "stats": {
        "season": "20242025",
        "games_played": 48,
        "wins": 22,
        "losses": 19,
        "ot_losses": 4,
        "save_percentage": 0.907,
        "goals_against_avg": 2.98,
        "shutouts": 2,
    },
}

_TEAM_EXTRACTED = {
    "name": "Edmonton Oilers",
    "abbrev": "EDM",
    "logo_url": "https://assets.nhle.com/logos/nhl/svg/EDM_light.svg",
    "stats": {
        "season": "20242025",
        "wins": 42,
        "losses": 20,
        "ot_losses": 5,
        "points": 89,
        "games_played": 67,
        "goals_for": 244,
        "goals_against": 201,
        "point_pct": 0.664,
    },
    "conference_rank": 3,
    "division_rank": 2,
}


class TestTranscriptPipeline:
    """SERV-05: _handle_transcript wires extract → stats → broadcast."""

    def _run(self, coro):
        return asyncio.run(coro)

    def test_player_transcript_broadcasts_player_payload(self):
        with (
            patch.object(server._extractor, "extract_entities",
                         return_value={"players": ["Connor McDavid"], "teams": []}),
            patch.object(server._stats_client, "lookup_player_id", return_value=8478402),
            patch.object(server._stats_client, "get_player",
                         new=AsyncMock(return_value=_SKATER_EXTRACTED)),
            patch("server.broadcast", new=AsyncMock()) as mock_bc,
        ):
            self._run(server._handle_transcript("McDavid scored tonight"))

        mock_bc.assert_called_once()
        payload = mock_bc.call_args[0][0]
        assert payload["type"] == "player"
        assert payload["id"] == 8478402
        assert payload["stats"]["goals"] == 32

    def test_goalie_transcript_broadcasts_goalie_payload(self):
        with (
            patch.object(server._extractor, "extract_entities",
                         return_value={"players": ["Jacob Markstrom"], "teams": []}),
            patch.object(server._stats_client, "lookup_player_id", return_value=8474593),
            patch.object(server._stats_client, "get_player",
                         new=AsyncMock(return_value=_GOALIE_EXTRACTED)),
            patch("server.broadcast", new=AsyncMock()) as mock_bc,
        ):
            self._run(server._handle_transcript("Markstrom with the save"))

        mock_bc.assert_called_once()
        payload = mock_bc.call_args[0][0]
        assert payload["type"] == "goalie"
        assert payload["stats"]["save_percentage"] == 0.907

    def test_team_transcript_broadcasts_team_payload(self):
        with (
            patch.object(server._extractor, "extract_entities",
                         return_value={"players": [], "teams": ["EDM"]}),
            patch.object(server._stats_client, "get_team",
                         new=AsyncMock(return_value=_TEAM_EXTRACTED)),
            patch("server.broadcast", new=AsyncMock()) as mock_bc,
        ):
            self._run(server._handle_transcript("The Oilers are leading"))

        mock_bc.assert_called_once()
        payload = mock_bc.call_args[0][0]
        assert payload["type"] == "team"
        assert payload["abbrev"] == "EDM"

    def test_player_and_team_both_broadcast(self):
        with (
            patch.object(server._extractor, "extract_entities",
                         return_value={"players": ["Connor McDavid"], "teams": ["EDM"]}),
            patch.object(server._stats_client, "lookup_player_id", return_value=8478402),
            patch.object(server._stats_client, "get_player",
                         new=AsyncMock(return_value=_SKATER_EXTRACTED)),
            patch.object(server._stats_client, "get_team",
                         new=AsyncMock(return_value=_TEAM_EXTRACTED)),
            patch("server.broadcast", new=AsyncMock()) as mock_bc,
        ):
            self._run(server._handle_transcript("McDavid scores for the Oilers"))

        assert mock_bc.call_count == 2
        types = {call[0][0]["type"] for call in mock_bc.call_args_list}
        assert types == {"player", "team"}

    def test_unknown_player_skips_broadcast(self):
        """Player not in players.json — lookup returns None → no broadcast."""
        with (
            patch.object(server._extractor, "extract_entities",
                         return_value={"players": ["Unknown Player"], "teams": []}),
            patch.object(server._stats_client, "lookup_player_id", return_value=None),
            patch("server.broadcast", new=AsyncMock()) as mock_bc,
        ):
            self._run(server._handle_transcript("Unknown Player scored"))

        mock_bc.assert_not_called()

    def test_stats_api_error_skips_broadcast(self):
        """get_player returns None (API error) → no broadcast."""
        with (
            patch.object(server._extractor, "extract_entities",
                         return_value={"players": ["Connor McDavid"], "teams": []}),
            patch.object(server._stats_client, "lookup_player_id", return_value=8478402),
            patch.object(server._stats_client, "get_player",
                         new=AsyncMock(return_value=None)),
            patch("server.broadcast", new=AsyncMock()) as mock_bc,
        ):
            self._run(server._handle_transcript("McDavid scored"))

        mock_bc.assert_not_called()

    def test_empty_transcript_skips_broadcast(self):
        with (
            patch.object(server._extractor, "extract_entities",
                         return_value={"players": [], "teams": []}),
            patch("server.broadcast", new=AsyncMock()) as mock_bc,
        ):
            self._run(server._handle_transcript(""))

        mock_bc.assert_not_called()


# ---------------------------------------------------------------------------
# SERV-08 — POST /debug/inject
# ---------------------------------------------------------------------------

class TestDebugInject:
    @pytest.fixture()
    def mock_player_broadcast(self):
        with patch("server._fetch_and_broadcast_player", new=AsyncMock()) as m:
            yield m

    @pytest.fixture()
    def mock_team_broadcast(self):
        with patch("server._fetch_and_broadcast_team", new=AsyncMock()) as m:
            yield m

    # ── player by id ──────────────────────────────────────────────────────

    def test_player_by_id_calls_broadcast(self, client, mock_player_broadcast):
        resp = client.post("/debug/inject", json={"type": "player", "id": 8478402})
        assert resp.status_code == 200
        assert resp.json() == {"ok": True}
        mock_player_broadcast.assert_called_once_with(8478402, "8478402")

    # ── player by name ────────────────────────────────────────────────────

    def test_player_by_name_resolves_and_broadcasts(self, client, mock_player_broadcast):
        with patch.object(server._stats_client, "lookup_player_id", return_value=8478402):
            resp = client.post("/debug/inject", json={"type": "player", "name": "Connor McDavid"})
        assert resp.status_code == 200
        mock_player_broadcast.assert_called_once_with(8478402, "Connor McDavid")

    def test_player_unknown_name_returns_404(self, client, mock_player_broadcast):
        with patch.object(server._stats_client, "lookup_player_id", return_value=None):
            resp = client.post("/debug/inject", json={"type": "player", "name": "Nobody"})
        assert resp.status_code == 404
        mock_player_broadcast.assert_not_called()

    def test_player_no_id_or_name_returns_422(self, client, mock_player_broadcast):
        resp = client.post("/debug/inject", json={"type": "player"})
        assert resp.status_code == 422
        mock_player_broadcast.assert_not_called()

    # ── team by abbrev ────────────────────────────────────────────────────

    def test_team_by_abbrev_calls_broadcast(self, client, mock_team_broadcast):
        resp = client.post("/debug/inject", json={"type": "team", "abbrev": "EDM"})
        assert resp.status_code == 200
        assert resp.json() == {"ok": True}
        mock_team_broadcast.assert_called_once_with("EDM")

    # ── team by name ──────────────────────────────────────────────────────

    def test_team_by_name_resolves_and_broadcasts(self, client, mock_team_broadcast):
        with patch.object(server._stats_client, "lookup_team_abbrev", return_value="EDM"):
            resp = client.post("/debug/inject", json={"type": "team", "name": "Edmonton Oilers"})
        assert resp.status_code == 200
        mock_team_broadcast.assert_called_once_with("EDM")

    def test_team_unknown_name_returns_404(self, client, mock_team_broadcast):
        with patch.object(server._stats_client, "lookup_team_abbrev", return_value=None):
            resp = client.post("/debug/inject", json={"type": "team", "name": "Fake Team"})
        assert resp.status_code == 404
        mock_team_broadcast.assert_not_called()

    def test_team_no_abbrev_or_name_returns_422(self, client, mock_team_broadcast):
        resp = client.post("/debug/inject", json={"type": "team"})
        assert resp.status_code == 422
        mock_team_broadcast.assert_not_called()

    # ── invalid type ──────────────────────────────────────────────────────

    def test_invalid_type_returns_422(self, client):
        resp = client.post("/debug/inject", json={"type": "goalie", "id": 8474593})
        assert resp.status_code == 422
