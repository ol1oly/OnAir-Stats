"""
Tests for search_player_id() — hits the live NHL search API.

Run from backend/:
    python tests/test_search_player_id.py
"""
from __future__ import annotations

import asyncio
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from stats import search_player_id


@dataclass
class TC:
    name:     str
    query:    str
    active:   bool | None
    expected: int | None    # None means we only check it is None


_CASES: list[TC] = [
    # Exact full-name matches (active players)
    TC("exact: Connor McDavid",          "Connor McDavid",     True,  8478402),
    TC("exact: Leon Draisaitl",          "Leon Draisaitl",     True,  8477934),
    TC("exact: Nathan MacKinnon",        "Nathan MacKinnon",   True,  8477492),
    TC("exact: Auston Matthews",         "Auston Matthews",    True,  8479318),
    TC("exact: David Pastrnak",          "David Pastrnak",     True,  8477956),

    # Surname-only (active=True default)
    TC("surname: McDavid",               "McDavid",            True,  8478402),
    TC("surname: Draisaitl",             "Draisaitl",          True,  8477934),
    TC("surname: MacKinnon",             "MacKinnon",          True,  8477492),

    # Case-insensitive
    TC("case: mcdavid lowercase",        "mcdavid",            True,  8478402),
    TC("case: MATTHEWS uppercase",       "MATTHEWS",           True,  8479318),

    # Retired player (active=False)
    TC("retired: Patrick Roy",           "Patrick Roy",        False, 8451033),

    # active=None includes both
    TC("any: Connor McDavid no filter",  "Connor McDavid",     None,  8478402),

    # No match
    TC("no match: gibberish",            "zzznobody",          True,  None),
    TC("no match: empty-ish query",      "xxxxxxxxxx",         True,  None),

    # ── Obscure / foreign names — exact full name ────────────────────────────
    TC("obscure: Kirill Kaprizov (Russian)",       "Kirill Kaprizov",    True,  8478864),
    TC("obscure: Juraj Slafkovsky (Slovak)",       "Juraj Slafkovsky",   True,  8483515),
    TC("obscure: Jesperi Kotkaniemi (Finnish)",    "Jesperi Kotkaniemi", True,  8480829),
    TC("obscure: Teuvo Teravainen (Finnish)",      "Teuvo Teravainen",   True,  8476882),
    TC("obscure: Yegor Sharangovich (Belarusian)", "Yegor Sharangovich", True,  8481068),
    TC("obscure: Pyotr Kochetkov (Russian)",       "Pyotr Kochetkov",    True,  8481611),
    TC("obscure: Nino Niederreiter (Swiss)",       "Nino Niederreiter",  True,  8475799),
    TC("obscure: Rasmus Dahlin (Swedish)",         "Rasmus Dahlin",      True,  8480839),
    TC("obscure: Ondrej Palat (Czech)",            "Ondrej Palat",       True,  8476292),
    TC("obscure: Radko Gudas (Czech)",             "Radko Gudas",        True,  8475462),
    TC("obscure: Ilya Sorokin (Russian)",          "Ilya Sorokin",       True,  8478009),
    TC("obscure: Pavel Buchnevich (Russian)",      "Pavel Buchnevich",   True,  8477402),
    TC("obscure: Logan Stankoven (unusual)",       "Logan Stankoven",    True,  8482702),
    TC("obscure: Marco Rossi (Swiss)",             "Marco Rossi",        True,  8482079),
    TC("obscure: Alexander Georgiev (Bulgarian)",  "Alexander Georgiev", True,  8482497),

    # ── Retired foreign players ──────────────────────────────────────────────
    TC("retired: Jakub Voracek (Czech)",           "Jakub Voracek",      False, 8474161),

    # ── Surname-only for foreign names ───────────────────────────────────────
    TC("surname: Kaprizov",      "Kaprizov",      True, 8478864),
    TC("surname: Kotkaniemi",    "Kotkaniemi",    True, 8480829),
    TC("surname: Slafkovsky",    "Slafkovsky",    True, 8483515),
    TC("surname: Niederreiter",  "Niederreiter",  True, 8475799),
    TC("surname: Teravainen",    "Teravainen",    True, 8476882),
    TC("surname: Sharangovich",  "Sharangovich",  True, 8481068),

    # ── Typos on foreign names — expected None (API can't recover) ───────────
    TC("typo: Kaprizof (v→f)",   "Kaprizof",      True, None),
]


async def _run() -> tuple[int, int]:
    passed = failed = 0
    for tc in _CASES:
        result = await search_player_id(tc.query, active=tc.active)
        ok = (result == tc.expected)
        if ok:
            passed += 1
            print(f"  pass  {tc.name}")
        else:
            failed += 1
            print(f"  FAIL  {tc.name}")
            print(f"        query    : {tc.query!r}  active={tc.active}")
            print(f"        expected : {tc.expected}")
            print(f"        got      : {result}")
    return passed, failed


if __name__ == "__main__":
    print(f"Running {len(_CASES)} tests (live API)…\n")
    _passed, _failed = asyncio.run(_run())
    total = _passed + _failed
    print(f"\n{'=' * 46}")
    print(f"  {_passed}/{total} passed", end="")
    if _failed:
        print(f"  —  {_failed} FAILED")
        sys.exit(1)
    else:
        print("  —  all good")
