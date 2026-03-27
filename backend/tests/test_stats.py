"""
Tests for StatsClient.get_player(), get_team(), and the build_*_payload() functions.

All tests mock httpx — no real network calls required.
Run from repo root:
    pytest backend/tests/test_stats.py -v
"""
from __future__ import annotations

import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = pytest.mark.anyio

from stats import (
    StatsClient,
    build_goalie_payload,
    build_player_payload,
    build_team_payload,
)

# ---------------------------------------------------------------------------
# Fixture data
# ---------------------------------------------------------------------------

_SKATER_API = {
    "playerId": 8478402,
    "position": "C",
    "firstName": {"default": "Connor"},
    "lastName": {"default": "McDavid"},
    "currentTeamAbbrev": "EDM",
    "headshot": "https://assets.nhle.com/mugs/nhl/skater/8478402.png",
    "featuredStats": {
        "season": 20242025,
        "regularSeason": {
            "subSeason": {
                "gamesPlayed": 62,
                "goals": 32,
                "assists": 100,
                "points": 132,
                "plusMinus": 15,
            }
        },
    },
}

_GOALIE_API = {
    "playerId": 8474593,
    "position": "G",
    "firstName": {"default": "Jacob"},
    "lastName": {"default": "Markstrom"},
    "currentTeamAbbrev": "NJD",
    "headshot": "https://assets.nhle.com/mugs/nhl/skater/8474593.png",
    "featuredStats": {
        "season": 20242025,
        "regularSeason": {
            "subSeason": {
                "gamesPlayed": 48,
                "wins": 22,
                "losses": 19,
                "otLosses": 4,
                "savePctg": 0.907,
                "goalsAgainstAvg": 2.98,
                "shutouts": 2,
            }
        },
    },
}

_STANDINGS_API = {
    "standings": [
        {
            "teamAbbrev": {"default": "EDM"},
            "teamName": {"default": "Edmonton Oilers"},
            "seasonId": 20242025,
            "wins": 42,
            "losses": 20,
            "otLosses": 5,
            "points": 89,
            "gamesPlayed": 67,
            "goalFor": 244,
            "goalAgainst": 201,
            "pointPctg": 0.664,
            "conferenceSequence": 3,
            "divisionSequence": 2,
        },
        {
            "teamAbbrev": {"default": "TOR"},
            "teamName": {"default": "Toronto Maple Leafs"},
            "seasonId": 20242025,
            "wins": 38,
            "losses": 25,
            "otLosses": 4,
            "points": 80,
            "gamesPlayed": 67,
            "goalFor": 220,
            "goalAgainst": 210,
            "pointPctg": 0.597,
            "conferenceSequence": 7,
            "divisionSequence": 4,
        },
    ],
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_response(json_data: dict, status_code: int = 200) -> MagicMock:
    resp = MagicMock()
    resp.json.return_value = json_data
    if status_code >= 400:
        from httpx import HTTPStatusError, Request, Response
        resp.raise_for_status.side_effect = HTTPStatusError(
            "error", request=MagicMock(), response=MagicMock()
        )
    else:
        resp.raise_for_status.return_value = None
    return resp


def _mock_client(response: MagicMock) -> MagicMock:
    """Return an async context manager mock whose .get() returns response."""
    client = AsyncMock()
    client.get = AsyncMock(return_value=response)
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=client)
    cm.__aexit__ = AsyncMock(return_value=False)
    return cm


# ---------------------------------------------------------------------------
# StatsClient.get_player — skater
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_get_player_skater_fields():
    client = StatsClient()
    cm = _mock_client(_mock_response(_SKATER_API))
    with patch("stats.httpx.AsyncClient", return_value=cm):
        result = await client.get_player(8478402, "Connor McDavid")

    assert result is not None
    assert result["_type"] == "skater"
    assert result["id"] == 8478402
    assert result["name"] == "Connor McDavid"
    assert result["team"] == "EDM"
    assert result["position"] == "C"
    assert "headshot_url" in result
    assert result["stats"]["season"] == "20242025"
    assert result["stats"]["games_played"] == 62
    assert result["stats"]["goals"] == 32
    assert result["stats"]["assists"] == 100
    assert result["stats"]["points"] == 132
    assert result["stats"]["plus_minus"] == 15
    # Goalie fields must NOT be present
    assert "save_percentage" not in result["stats"]


# ---------------------------------------------------------------------------
# StatsClient.get_player — goalie
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_get_player_goalie_fields():
    client = StatsClient()
    cm = _mock_client(_mock_response(_GOALIE_API))
    with patch("stats.httpx.AsyncClient", return_value=cm):
        result = await client.get_player(8474593, "Jacob Markstrom")

    assert result is not None
    assert result["_type"] == "goalie"
    assert result["id"] == 8474593
    assert result["position"] == "G"
    assert result["stats"]["wins"] == 22
    assert result["stats"]["losses"] == 19
    assert result["stats"]["ot_losses"] == 4
    assert result["stats"]["save_percentage"] == pytest.approx(0.907)
    assert result["stats"]["goals_against_avg"] == pytest.approx(2.98)
    assert result["stats"]["shutouts"] == 2
    # Skater fields must NOT be present
    assert "goals" not in result["stats"]
    assert "assists" not in result["stats"]


# ---------------------------------------------------------------------------
# StatsClient.get_player — HTTP error → None
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_get_player_http_error_returns_none():
    client = StatsClient()
    cm = _mock_client(_mock_response({}, status_code=404))
    with patch("stats.httpx.AsyncClient", return_value=cm):
        result = await client.get_player(9999999, "Unknown")
    assert result is None


# ---------------------------------------------------------------------------
# StatsClient.get_player — cache hit: only one HTTP call for two invocations
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_get_player_cache_hit():
    client = StatsClient()
    cm = _mock_client(_mock_response(_SKATER_API))
    with patch("stats.httpx.AsyncClient", return_value=cm) as mock_cls:
        await client.get_player(8478402, "Connor McDavid")
        await client.get_player(8478402, "Connor McDavid")
    # AsyncClient should only have been instantiated once
    assert mock_cls.call_count == 1


# ---------------------------------------------------------------------------
# StatsClient.get_team — valid abbrev
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_get_team_fields():
    client = StatsClient()
    cm = _mock_client(_mock_response(_STANDINGS_API))
    with patch("stats.httpx.AsyncClient", return_value=cm):
        result = await client.get_team("EDM")

    assert result is not None
    assert result["name"] == "Edmonton Oilers"
    assert result["abbrev"] == "EDM"
    assert result["logo_url"] == "https://assets.nhle.com/logos/nhl/svg/EDM_light.svg"
    assert result["stats"]["season"] == "20242025"
    assert result["stats"]["wins"] == 42
    assert result["stats"]["losses"] == 20
    assert result["stats"]["ot_losses"] == 5
    assert result["stats"]["points"] == 89
    assert result["stats"]["games_played"] == 67
    assert result["stats"]["goals_for"] == 244
    assert result["stats"]["goals_against"] == 201
    assert result["stats"]["point_pct"] == pytest.approx(0.664)
    assert result["conference_rank"] == 3
    assert result["division_rank"] == 2


# ---------------------------------------------------------------------------
# StatsClient.get_team — case-insensitive abbrev
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_get_team_case_insensitive():
    client = StatsClient()
    cm = _mock_client(_mock_response(_STANDINGS_API))
    with patch("stats.httpx.AsyncClient", return_value=cm):
        result = await client.get_team("edm")
    assert result is not None
    assert result["abbrev"] == "EDM"


# ---------------------------------------------------------------------------
# StatsClient.get_team — team not in standings → None
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_get_team_not_found_returns_none():
    client = StatsClient()
    cm = _mock_client(_mock_response(_STANDINGS_API))
    with patch("stats.httpx.AsyncClient", return_value=cm):
        result = await client.get_team("XYZ")
    assert result is None


# ---------------------------------------------------------------------------
# StatsClient.get_team — HTTP error → None
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_get_team_http_error_returns_none():
    client = StatsClient()
    cm = _mock_client(_mock_response({}, status_code=500))
    with patch("stats.httpx.AsyncClient", return_value=cm):
        result = await client.get_team("EDM")
    assert result is None


# ---------------------------------------------------------------------------
# StatsClient.get_team — cache hit: standings fetched only once
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_get_team_cache_hit():
    client = StatsClient()
    cm = _mock_client(_mock_response(_STANDINGS_API))
    with patch("stats.httpx.AsyncClient", return_value=cm) as mock_cls:
        await client.get_team("EDM")
        await client.get_team("TOR")  # different team, same standings fetch
    assert mock_cls.call_count == 1


# ---------------------------------------------------------------------------
# build_player_payload
# ---------------------------------------------------------------------------

def _skater_extracted() -> dict:
    return {
        "_type": "skater",
        "id": 8478402,
        "name": "Connor McDavid",
        "team": "EDM",
        "position": "C",
        "headshot_url": "https://assets.nhle.com/mugs/nhl/skater/8478402.png",
        "stats": {
            "season": "20242025",
            "games_played": 62,
            "goals": 32,
            "assists": 100,
            "points": 132,
            "plus_minus": 15,
        },
    }


def test_build_player_payload_type():
    p = build_player_payload(_skater_extracted())
    assert p["type"] == "player"


def test_build_player_payload_display():
    p = build_player_payload(_skater_extracted())
    assert p["display"] == "McDavid · 32G  100A  132PTS  +15"


def test_build_player_payload_negative_plus_minus():
    ext = _skater_extracted()
    ext["stats"]["plus_minus"] = -5
    p = build_player_payload(ext)
    assert "-5" in p["display"]
    assert "+" not in p["display"]


def test_build_player_payload_ts_recent():
    before = int(time.time() * 1000)
    p = build_player_payload(_skater_extracted())
    after = int(time.time() * 1000)
    assert before <= p["ts"] <= after


# ---------------------------------------------------------------------------
# build_goalie_payload
# ---------------------------------------------------------------------------

def _goalie_extracted() -> dict:
    return {
        "_type": "goalie",
        "id": 8474593,
        "name": "Jacob Markstrom",
        "team": "NJD",
        "position": "G",
        "headshot_url": "https://assets.nhle.com/mugs/nhl/skater/8474593.png",
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


def test_build_goalie_payload_type():
    p = build_goalie_payload(_goalie_extracted())
    assert p["type"] == "goalie"


def test_build_goalie_payload_display():
    p = build_goalie_payload(_goalie_extracted())
    assert p["display"] == "Markstrom · .907 SV%  2.98 GAA  2 SO"


def test_build_goalie_payload_ts_recent():
    before = int(time.time() * 1000)
    p = build_goalie_payload(_goalie_extracted())
    after = int(time.time() * 1000)
    assert before <= p["ts"] <= after


# ---------------------------------------------------------------------------
# build_team_payload
# ---------------------------------------------------------------------------

def _team_extracted() -> dict:
    return {
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


def test_build_team_payload_type():
    p = build_team_payload(_team_extracted())
    assert p["type"] == "team"


def test_build_team_payload_display():
    p = build_team_payload(_team_extracted())
    assert p["display"] == "EDM · 42W  20L  5OT  89PTS"


def test_build_team_payload_ts_recent():
    before = int(time.time() * 1000)
    p = build_team_payload(_team_extracted())
    after = int(time.time() * 1000)
    assert before <= p["ts"] <= after
