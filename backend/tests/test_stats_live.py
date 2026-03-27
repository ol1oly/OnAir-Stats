"""
Live NHL API tests for StatsClient.get_player() and get_team().

Hits real endpoints — requires internet access. No mocking.
Timing is recorded for every call.

Run from repo root:
    python backend/tests/test_stats_live.py
"""
from __future__ import annotations

import asyncio
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent))

from stats import StatsClient, build_goalie_payload, build_player_payload, build_team_payload

client = StatsClient()


# ---------------------------------------------------------------------------
# Result container
# ---------------------------------------------------------------------------

@dataclass
class Result:
    name:    str
    ok:      bool
    elapsed: float          # seconds
    error:   str = ""
    notes:   list[str] = field(default_factory=list)


results: list[Result] = []


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _check(result: Result, condition: bool, msg: str) -> None:
    if not condition:
        result.ok = False
        result.notes.append(f"FAIL  {msg}")
    else:
        result.notes.append(f"pass  {msg}")


async def _timed(coro) -> tuple[Any, float]:
    t0 = time.perf_counter()
    value = await coro
    return value, time.perf_counter() - t0


# ---------------------------------------------------------------------------
# get_player — skaters
# ---------------------------------------------------------------------------

_SKATERS = [
    (8478402, "Connor McDavid",   "C"),
    (8477934, "Leon Draisaitl",   "C"),
    (8477492, "Nathan MacKinnon", "C"),
    (8479318, "Auston Matthews",  "C"),
    (8477956, "David Pastrnak",   "R"),
]

_GOALIES = [
    (8476883, "Connor Hellebuyck"),
    (8478009, "Ilya Sorokin"),
]


_SKATER_POSITIONS = {"C", "L", "R", "D"}


async def test_skater(player_id: int, name: str, position: str) -> Result:
    r = Result(name=f"get_player skater  {name}", ok=True, elapsed=0.0)
    extracted, r.elapsed = await _timed(client.get_player(player_id, name))

    if extracted is None:
        r.ok = False
        r.error = "returned None"
        return r

    _check(r, extracted["_type"] == "skater",                          "_type == 'skater'")
    _check(r, extracted["id"] == player_id,                            f"id == {player_id}")
    _check(r, extracted["name"] == name,                               f"name == '{name}'")
    _check(r, extracted["position"] == position,                       f"position == '{position}'")
    _check(r, extracted["position"] in _SKATER_POSITIONS,              f"position in valid set")
    _check(r, isinstance(extracted["team"], str) and len(extracted["team"]) in (3, 4),
                                                                       "team is a 3-4 char abbrev")
    _check(r, extracted["headshot_url"].startswith("https://"),        "headshot_url is a URL")
    _check(r, len(extracted["stats"]["season"]) == 8,                  "season is 8-char string")
    _check(r, extracted["stats"]["games_played"] > 0,                  "games_played > 0")
    _check(r, extracted["stats"]["goals"] >= 0,                        "goals >= 0")
    _check(r, extracted["stats"]["assists"] >= 0,                      "assists >= 0")
    _check(r, extracted["stats"]["points"] >= 0,                       "points >= 0")
    _check(r, "save_percentage" not in extracted["stats"],             "no goalie fields on skater")

    # Smoke-test the builder
    payload = build_player_payload(extracted)
    last_name = name.split()[-1]
    _check(r, payload["type"] == "player",                             "build_player_payload.type == 'player'")
    _check(r, last_name in payload["display"],                         f"display contains '{last_name}'")
    _check(r, "PTS" in payload["display"],                             "display contains PTS")

    return r


async def test_goalie(player_id: int, name: str) -> Result:
    r = Result(name=f"get_player goalie  {name}", ok=True, elapsed=0.0)
    extracted, r.elapsed = await _timed(client.get_player(player_id, name))

    if extracted is None:
        r.ok = False
        r.error = "returned None"
        return r

    _check(r, extracted["_type"] == "goalie",                          "_type == 'goalie'")
    _check(r, extracted["id"] == player_id,                            f"id == {player_id}")
    _check(r, extracted["position"] == "G",                            "position == 'G'")
    _check(r, isinstance(extracted["team"], str) and len(extracted["team"]) in (3, 4),
                                                                       "team is a 3-4 char abbrev")
    _check(r, extracted["headshot_url"].startswith("https://"),        "headshot_url is a URL")
    _check(r, extracted["stats"]["games_played"] > 0,                  "games_played > 0")
    _check(r, 0.8 < extracted["stats"]["save_percentage"] < 1,        "save_percentage in (0.8, 1)")
    _check(r, extracted["stats"]["goals_against_avg"] > 0,             "goals_against_avg > 0")
    _check(r, extracted["stats"]["shutouts"] >= 0,                     "shutouts >= 0")
    _check(r, "goals" not in extracted["stats"],                       "no skater fields on goalie")

    # Smoke-test the builder
    payload = build_goalie_payload(extracted)
    _check(r, payload["type"] == "goalie",                             "build_goalie_payload.type == 'goalie'")
    _check(r, "SV%" in payload["display"],                             "display contains SV%")
    _check(r, "GAA" in payload["display"],                             "display contains GAA")
    _check(r, "SO"  in payload["display"],                             "display contains SO")

    return r


# ---------------------------------------------------------------------------
# get_player — cache: second call must be faster and return same data
# ---------------------------------------------------------------------------

async def test_player_cache(player_id: int, name: str) -> Result:
    r = Result(name=f"get_player cache   {name}", ok=True, elapsed=0.0)

    fresh = StatsClient()  # isolated client — guaranteed cold cache
    first,  t1 = await _timed(fresh.get_player(player_id, name))
    second, t2 = await _timed(fresh.get_player(player_id, name))
    r.elapsed = t1  # report the network call duration

    _check(r, first is not None,   "first call returned data")
    _check(r, second is not None,  "second call returned data")
    _check(r, first == second,     "cached result is identical")
    _check(r, t2 < t1 * 0.1,      f"cache hit fast: {t2*1000:.2f}ms vs {t1*1000:.1f}ms")

    return r


# ---------------------------------------------------------------------------
# get_team
# ---------------------------------------------------------------------------

_TEAMS = [
    ("EDM", "Edmonton Oilers"),
    ("TOR", "Toronto Maple Leafs"),
    ("BOS", "Boston Bruins"),
    ("NYR", "New York Rangers"),
    ("COL", "Colorado Avalanche"),
]


async def test_team(abbrev: str, expected_name: str) -> Result:
    r = Result(name=f"get_team           {abbrev}", ok=True, elapsed=0.0)
    extracted, r.elapsed = await _timed(client.get_team(abbrev))

    if extracted is None:
        r.ok = False
        r.error = "returned None"
        return r

    _check(r, extracted["name"] == expected_name,                   f"name == '{expected_name}'")
    _check(r, extracted["abbrev"] == abbrev,                        f"abbrev == '{abbrev}'")
    _check(r, f"/{abbrev}_light.svg" in extracted["logo_url"],      "logo_url contains abbrev")
    _check(r, extracted["logo_url"].startswith("https://"),         "logo_url is a URL")
    _check(r, len(extracted["stats"]["season"]) == 8,               "season is 8-char string")
    _check(r, extracted["stats"]["games_played"] > 0,               "games_played > 0")
    _check(r, extracted["stats"]["wins"] >= 0,                      "wins >= 0")
    _check(r, extracted["stats"]["losses"] >= 0,                    "losses >= 0")
    _check(r, extracted["stats"]["points"] >= 0,                    "points >= 0")
    _check(r, 0 < extracted["stats"]["point_pct"] < 1,              "point_pct in (0, 1)")
    _check(r, extracted["conference_rank"] >= 1,                    "conference_rank >= 1")
    _check(r, extracted["division_rank"] >= 1,                      "division_rank >= 1")

    # Smoke-test the builder
    payload = build_team_payload(extracted)
    _check(r, payload["type"] == "team",                            "build_team_payload.type == 'team'")
    _check(r, abbrev in payload["display"],                         "display contains abbrev")

    return r


# ---------------------------------------------------------------------------
# get_team — standings cache: all 5 teams share a single HTTP fetch
# ---------------------------------------------------------------------------

async def test_team_cache() -> Result:
    r = Result(name="get_team cache     (5 teams, 1 fetch)", ok=True, elapsed=0.0)

    fresh = StatsClient()  # isolated client with empty cache
    times: list[float] = []
    for abbrev, _ in _TEAMS:
        _, elapsed = await _timed(fresh.get_team(abbrev))
        times.append(elapsed)

    r.elapsed = times[0]
    first_ms  = times[0] * 1000
    cached_ms = max(times[1:]) * 1000

    _check(r, all(t is not None for t in times), "all 5 teams returned data")
    _check(r, cached_ms < first_ms * 0.1,
           f"cache hits fast: max={cached_ms:.1f}ms vs first={first_ms:.1f}ms")

    return r


# ---------------------------------------------------------------------------
# get_team — unknown abbrev → None
# ---------------------------------------------------------------------------

async def test_team_unknown() -> Result:
    r = Result(name="get_team unknown   XYZ", ok=True, elapsed=0.0)
    result, r.elapsed = await _timed(client.get_team("XYZ"))
    _check(r, result is None, "unknown abbrev returns None")
    return r


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

async def _run_all() -> list[Result]:
    all_results: list[Result] = []

    # Skaters
    for pid, name, pos in _SKATERS:
        all_results.append(await test_skater(pid, name, pos))

    # Goalies
    for pid, name in _GOALIES:
        all_results.append(await test_goalie(pid, name))

    # Player cache (use McDavid — already warm from above)
    all_results.append(await test_player_cache(8478402, "Connor McDavid"))

    # Teams
    for abbrev, name in _TEAMS:
        all_results.append(await test_team(abbrev, name))

    # Team cache
    all_results.append(await test_team_cache())

    # Unknown team
    all_results.append(await test_team_unknown())

    return all_results


def _print_results(all_results: list[Result]) -> int:
    col_w = max(len(r.name) for r in all_results) + 2
    sep = "-" * (col_w + 52)

    print(f"\n{sep}")
    print(f"  {'Test':<{col_w}}  {'Status':<8}  {'Time':>8}  Notes")
    print(sep)

    failed = 0
    for r in all_results:
        status = "PASS" if r.ok else "FAIL"
        time_str = f"{r.elapsed * 1000:>7.1f}ms"
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
    print(f"  {passed}/{len(all_results)} passed", end="")
    if failed:
        print(f"  —  {failed} FAILED")
    else:
        print("  —  all good")
    print(sep)
    return failed


if __name__ == "__main__":
    print("NHL API live tests — hitting real endpoints…")
    all_results = asyncio.run(_run_all())
    failed = _print_results(all_results)
    sys.exit(1 if failed else 0)
