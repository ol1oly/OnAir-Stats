"""NHL stats lookup and API client."""
from __future__ import annotations

import json
from pathlib import Path
from typing import TypedDict
import httpx
from rapidfuzz import fuzz, process

DATA_DIR = Path(__file__).parent


# ---------------------------------------------------------------------------
# Payload types
# ---------------------------------------------------------------------------

class PlayerPayload(TypedDict):
    type: str       # always "player"
    player: str
    stats: dict
    display: str


class TeamPayload(TypedDict):
    type: str       # always "team"
    team: str
    abbrev: str
    stats: dict
    display: str


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _load_players() -> dict[str, int]:
    with open(DATA_DIR / "players.json", encoding="utf-8") as f:
        return json.load(f)


def _load_teams() -> dict[str, str]:
    with open(DATA_DIR / "teams.json", encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# STATS-03: lookup_player_id
# ---------------------------------------------------------------------------

def lookup_player_id(name: str) -> int | None:
    """Case-insensitive player name → NHL player ID. Returns None if not found."""
    players = _load_players()
    name_lower = name.lower()
    for k, v in players.items():
        if k.lower() == name_lower:
            return v
    return None


# ---------------------------------------------------------------------------
# STATS-04: lookup_team_abbrev
# ---------------------------------------------------------------------------

def lookup_team_abbrev(name: str) -> str | None:
    """Case-insensitive team name / alias / city → abbreviation. Returns None if not found."""
    teams = _load_teams()
    name_lower = name.lower()
    for k, v in teams.items():
        if k.lower() == name_lower:
            return v
    return None


# ---------------------------------------------------------------------------
# Live NHL search API — resolve any player name to an ID
# ---------------------------------------------------------------------------

_SEARCH_URL = "https://search.d3.nhle.com/api/v1/search/player"
_SEARCH_THRESHOLD = 85  # minimum fuzz.ratio score for fuzzy name fallback


async def search_player_id(name: str, active: bool | None = True) -> int | None:
    """
    Search the NHL API for a player by name and return their player ID.

    Parameters
    ----------
    name:   Player name to search (any capitalisation or minor spelling variation).
    active: True  → only active (current) players
            False → only inactive (retired) players
            None  → no filter

    Returns the player ID as int, or None if no confident match was found.
    Never raises — returns None on any network or parse error.
    """
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(
                _SEARCH_URL,
                params={"culture": "en-us", "active" : active,"limit": 20, "q": name},
            )
            resp.raise_for_status()
            results: list[dict] = resp.json()
    except Exception:
        return None

    if not results:
        return None

    

    if not results:
        return None

    # Exact case-insensitive match first
    name_lower = name.lower()
    for r in results:
        if r.get("name", "").lower() == name_lower:
            return int(r["playerId"])

    # Fuzzy fallback — partial_ratio handles surname-only input (e.g. "mcdavid" in "Connor McDavid")
    # Compare lowercased to avoid case sensitivity issues
    names_lower = [r.get("name", "").lower() for r in results]
    hit = process.extractOne(name.lower(), names_lower, scorer=fuzz.partial_ratio, score_cutoff=_SEARCH_THRESHOLD)
    if hit:
        return int(results[hit[2]]["playerId"])

    return None


# ---------------------------------------------------------------------------
# StatsClient — caching NHL API client (STATS-05 through STATS-09 pending)
# ---------------------------------------------------------------------------

class StatsClient:
    """
    Wraps NHL API calls with a 45-second in-memory cache.
    Lookup methods load data once at construction time for efficiency.
    Full API implementation added in STATS-05/06/07.
    """

    def __init__(self) -> None:
        raw_players = _load_players()
        raw_teams = _load_teams()
        self._players_lower: dict[str, int] = {k.lower(): v for k, v in raw_players.items()}
        self._teams_lower: dict[str, str] = {k.lower(): v for k, v in raw_teams.items()}

    def lookup_player_id(self, name: str) -> int | None:
        """Case-insensitive player name → NHL player ID."""
        return self._players_lower.get(name.lower())

    def lookup_team_abbrev(self, name: str) -> str | None:
        """Case-insensitive team name / alias / city → abbreviation."""
        return self._teams_lower.get(name.lower())

    async def get_player(self, player_id: int, name: str) -> PlayerPayload | None:
        """Fetch live player stats. Implemented in STATS-05."""
        raise NotImplementedError("StatsClient.get_player() requires STATS-05 implementation")

    async def get_team(self, abbrev: str) -> TeamPayload | None:
        """Fetch live team standings stats. Implemented in STATS-06."""
        raise NotImplementedError("StatsClient.get_team() requires STATS-06 implementation")
