"""Shared infrastructure for standalone live-API test scripts.

Used by test_stats_live.py and test_server_live.py — not imported by pytest.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Result:
    name:    str
    ok:      bool  = True
    elapsed: float = 0.0
    error:   str   = ""
    notes:   list[str] = field(default_factory=list)


def check(r: Result, condition: bool, msg: str) -> None:
    """Append a pass/FAIL note to *r* and flip *r.ok* on failure."""
    if not condition:
        r.ok = False
        r.notes.append(f"FAIL  {msg}")
    else:
        r.notes.append(f"pass  {msg}")


async def timed(coro) -> tuple[Any, float]:
    """Await *coro* and return (value, elapsed_seconds)."""
    t0 = time.perf_counter()
    value = await coro
    return value, time.perf_counter() - t0


def print_results(all_results: list[Result]) -> int:
    """Pretty-print a results table. Returns the number of failures."""
    col_w = max(len(r.name) for r in all_results) + 2
    sep = "-" * (col_w + 52)

    print(f"\n{sep}")
    print(f"  {'Test':<{col_w}}  {'Status':<8}  {'Time':>9}  Notes")
    print(sep)

    failed = 0
    for r in all_results:
        status = "PASS" if r.ok else "FAIL"
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
