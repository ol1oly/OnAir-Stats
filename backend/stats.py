"""NHL stats lookup and API client."""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import TypedDict
import httpx
from rapidfuzz import fuzz, process

from config import (
    NHL_API_BASE,
    NHL_CACHE_TTL,
    NHL_HTTP_TIMEOUT,
    NHL_LOGO_TEMPLATE,
    NHL_SEARCH_URL,
    SEARCH_MATCH_THRESHOLD,
)

DATA_DIR = Path(__file__).parent


# ---------------------------------------------------------------------------
# Payload types (mirrors ws-payload-contract.md)
# ---------------------------------------------------------------------------

class _PlayerStats(TypedDict):
    season: str
    games_played: int
    goals: int
    assists: int
    points: int
    plus_minus: int


class PlayerPayload(TypedDict):
    type: str           # "player"
    id: int
    name: str
    team: str
    position: str
    headshot_url: str
    stats: _PlayerStats
    display: str
    ts: int


class _GoalieStats(TypedDict):
    season: str
    games_played: int
    wins: int
    losses: int
    ot_losses: int
    save_percentage: float
    goals_against_avg: float
    shutouts: int


class GoaliePayload(TypedDict):
    type: str           # "goalie"
    id: int
    name: str
    team: str
    headshot_url: str
    stats: _GoalieStats
    display: str
    ts: int


class _TeamStats(TypedDict):
    season: str
    wins: int
    losses: int
    ot_losses: int
    points: int
    games_played: int
    goals_for: int
    goals_against: int
    point_pct: float


class TeamPayload(TypedDict):
    type: str           # "team"
    name: str
    abbrev: str
    logo_url: str
    stats: _TeamStats
    conference_rank: int
    division_rank: int
    display: str
    ts: int


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
        async with httpx.AsyncClient(timeout=NHL_HTTP_TIMEOUT) as client:
            resp = await client.get(
                NHL_SEARCH_URL,
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
    hit = process.extractOne(name.lower(), names_lower, scorer=fuzz.partial_ratio, score_cutoff=SEARCH_MATCH_THRESHOLD)
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
    """

    def __init__(self) -> None:
        raw_players = _load_players()
        raw_teams = _load_teams()
        self._players_lower: dict[str, int] = {k.lower(): v for k, v in raw_players.items()}
        self._teams_lower: dict[str, str] = {k.lower(): v for k, v in raw_teams.items()}
        self._cache: dict[str, tuple[float, dict]] = {}

    def lookup_player_id(self, name: str) -> int | None:
        """Case-insensitive player name → NHL player ID."""
        return self._players_lower.get(name.lower())

    def lookup_team_abbrev(self, name: str) -> str | None:
        """Case-insensitive team name / alias / city → abbreviation."""
        return self._teams_lower.get(name.lower())

    def _cache_get(self, key: str) -> dict | None:
        entry = self._cache.get(key)
        if entry and time.monotonic() - entry[0] < NHL_CACHE_TTL:
            return entry[1]
        return None

    def _cache_set(self, key: str, value: dict) -> None:
        self._cache[key] = (time.monotonic(), value)

    async def get_player(self, player_id: int, name: str) -> dict | None:
        """
        Fetch and extract player stats from the NHL API.

        Returns an intermediate extracted dict (not a broadcast payload).
        The dict has a `_type` key: "skater" or "goalie".
        Caller should pass the result to build_player_payload() or build_goalie_payload().
        Returns None on any HTTP or parse error.
        """
        cache_key = f"player:{player_id}"
        cached = self._cache_get(cache_key)
        if cached is not None:
            return cached

        try:
            async with httpx.AsyncClient(timeout=NHL_HTTP_TIMEOUT, follow_redirects=True) as client:
                resp = await client.get(f"{NHL_API_BASE}/player/{player_id}/landing")
                resp.raise_for_status()
                data = resp.json()
        except Exception:
            return None

        try:
            position = data["position"]
            sub = data["featuredStats"]["regularSeason"]["subSeason"]
            extracted: dict = {
                "_type": "goalie" if position == "G" else "skater",
                "id": data["playerId"],
                "name": f"{data['firstName']['default']} {data['lastName']['default']}",
                "team": data["currentTeamAbbrev"],
                "position": position,
                "headshot_url": data["headshot"],
                "stats": {
                    "season": str(data["featuredStats"]["season"]),
                    "games_played": sub["gamesPlayed"],
                },
            }
            if position == "G":
                extracted["stats"].update({
                    "wins": sub["wins"],
                    "losses": sub["losses"],
                    "ot_losses": sub["otLosses"],
                    "save_percentage": sub["savePctg"],
                    "goals_against_avg": sub["goalsAgainstAvg"],
                    "shutouts": sub["shutouts"],
                })
            else:
                extracted["stats"].update({
                    "goals": sub["goals"],
                    "assists": sub["assists"],
                    "points": sub["points"],
                    "plus_minus": sub["plusMinus"],
                })
        except (KeyError, TypeError):
            return None

        self._cache_set(cache_key, extracted)
        return extracted

    async def get_team(self, abbrev: str) -> dict | None:
        """
        Fetch and extract team standings from the NHL API.

        Returns an intermediate extracted dict (not a broadcast payload).
        Caller should pass the result to build_team_payload().
        Returns None if the team is not found or on any HTTP/parse error.
        """
        standings = self._cache_get("standings")
        if standings is None:
            try:
                async with httpx.AsyncClient(timeout=NHL_HTTP_TIMEOUT, follow_redirects=True) as client:
                    resp = await client.get(f"{NHL_API_BASE}/standings/now")
                    resp.raise_for_status()
                    standings = resp.json()
            except Exception:
                return None
            self._cache_set("standings", standings)

        abbrev_upper = abbrev.upper()
        try:
            team_entry = next(
                (t for t in standings["standings"]
                 if t["teamAbbrev"]["default"].upper() == abbrev_upper),
                None,
            )
        except (KeyError, TypeError):
            return None

        if team_entry is None:
            return None

        try:
            extracted = {
                "name": team_entry["teamName"]["default"],
                "abbrev": team_entry["teamAbbrev"]["default"],
                "logo_url": NHL_LOGO_TEMPLATE.format(abbrev=abbrev_upper),
                "stats": {
                    "season": str(team_entry["seasonId"]),
                    "wins": team_entry["wins"],
                    "losses": team_entry["losses"],
                    "ot_losses": team_entry["otLosses"],
                    "points": team_entry["points"],
                    "games_played": team_entry["gamesPlayed"],
                    "goals_for": team_entry["goalFor"],
                    "goals_against": team_entry["goalAgainst"],
                    "point_pct": team_entry["pointPctg"],
                },
                "conference_rank": team_entry["conferenceSequence"],
                "division_rank": team_entry["divisionSequence"],
            }
        except (KeyError, TypeError):
            return None

        return extracted


# ---------------------------------------------------------------------------
# Payload builders — add display string + ts to extracted dicts
# ---------------------------------------------------------------------------

def build_player_payload(extracted: dict) -> PlayerPayload:
    """Format a skater extracted dict into a broadcast-ready PlayerPayload."""
    s = extracted["stats"]
    pm = s["plus_minus"]
    pm_str = f"+{pm}" if pm >= 0 else str(pm)
    display = (
        f"{extracted['name'].split()[-1]} · "
        f"{s['goals']}G  {s['assists']}A  {s['points']}PTS  {pm_str}"
    )
    return {
        "type": "player",
        "id": extracted["id"],
        "name": extracted["name"],
        "team": extracted["team"],
        "position": extracted["position"],
        "headshot_url": extracted["headshot_url"],
        "stats": s,
        "display": display,
        "ts": int(time.time() * 1000),
    }


def build_goalie_payload(extracted: dict) -> GoaliePayload:
    """Format a goalie extracted dict into a broadcast-ready GoaliePayload."""
    s = extracted["stats"]
    sv = f"{s['save_percentage']:.3f}".lstrip("0") or "0"  # ".912" not "0.912"
    display = (
        f"{extracted['name'].split()[-1]} · "
        f"{sv} SV%  {s['goals_against_avg']:.2f} GAA  {s['shutouts']} SO"
    )
    return {
        "type": "goalie",
        "id": extracted["id"],
        "name": extracted["name"],
        "team": extracted["team"],
        "headshot_url": extracted["headshot_url"],
        "stats": s,
        "display": display,
        "ts": int(time.time() * 1000),
    }


def build_team_payload(extracted: dict) -> TeamPayload:
    """Format a team extracted dict into a broadcast-ready TeamPayload."""
    s = extracted["stats"]
    display = (
        f"{extracted['abbrev']} · "
        f"{s['wins']}W  {s['losses']}L  {s['ot_losses']}OT  {s['points']}PTS"
    )
    return {
        "type": "team",
        "name": extracted["name"],
        "abbrev": extracted["abbrev"],
        "logo_url": extracted["logo_url"],
        "stats": s,
        "conference_rank": extracted["conference_rank"],
        "division_rank": extracted["division_rank"],
        "display": display,
        "ts": int(time.time() * 1000),
    }
