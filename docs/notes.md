# Notes

---

## Keyword-based action extraction in `extract_entities`

**Date:** 2026-03-24

Currently `extract_entities` returns players and teams only:

```python
{"players": ["Connor McDavid"], "teams": ["TOR"]}
```

**Idea:** add an `actions` field by detecting hockey-action keywords in the transcript. For example:

> *"McDavid scores tonight against the Leafs"*

could return:

```python
{"players": ["Connor McDavid"], "teams": ["TOR"], "actions": ["scoring"]}
```

### Potential keyword groups

| Action | Keywords |
|---|---|
| `scoring` | scores, scored, goal, buries, taps in, fires, buries it, snaps |
| `assist` | assists, sets up, feeds, dishes, pass, thread |
| `penalty` | penalty, hooking, tripping, slashing, interference, high-sticking |
| `fight` | fight, drops the gloves, scrap, tilt |
| `save` | save, stops, robs, denies, kicks out |
| `hit` | hit, crushes, lays out, boards |

### Usage in the pipeline

The `actions` field could be used by the server to:
- Prioritize which stat card to show (e.g. show goals stat when action is `scoring`)
- Trigger specific overlays (e.g. a fight card, or a goalie save highlight)
- Filter out low-signal mentions (e.g. a player name mentioned in passing with no action)

### Implementation sketch

A simple pass over the tokenized transcript checking for keyword membership — no fuzzy matching needed since these are common English words. Could be a `set`-based lookup added at the end of `extract_entities`, returning `[]` if no keywords matched.

---

## Background roster pre-fetch on team mention

**Date:** 2026-03-27

When a team is detected in the transcript, proactively fetch and cache key players from that team in the background — so if the commentator then mentions a player by name, the stat card appears instantly instead of waiting on a cold API call.

### What to pre-fetch

**Team roster (`GET /v1/roster/{abbrev}/current`)**
Returns the full active roster with player IDs and positions. No need to store everything — filter down to:
- The captain and alternate captains (`captaincy` field: `"C"` or `"A"`)
- The top-line forwards (roster slot 1–4 by sweater number, or by sorting on `featuredStats.points` once fetched)
- The starting goalie (can be inferred from games played once stats are fetched)

In practice, fetching 5–8 players per team covers most of what commentary will mention.

**Opposing team on game day**
If the detected team has a game today, also pre-fetch that opponent's key players.
- `GET /v1/club-schedule/{abbrev}/week/now` — returns upcoming games for the team; check for a game with `gameDate == today`
- Extract `homeTeam.abbrev` / `awayTeam.abbrev` to identify the opponent, then trigger the same roster pre-fetch for them

### Pipeline sketch

```
on entity_extracted(teams=[...]):
    for team_abbrev in teams:
        asyncio.create_task(_prefetch_team(team_abbrev))   # fire-and-forget

async def _prefetch_team(abbrev):
    roster = await fetch_roster(abbrev)           # /v1/roster/{abbrev}/current
    key_players = filter_key_players(roster)      # captains + top forwards + starter goalie
    for player_id in key_players:
        await client.get_player(player_id, ...)   # warms the cache silently

    opponent = await get_todays_opponent(abbrev)  # /v1/club-schedule/.../week/now
    if opponent:
        asyncio.create_task(_prefetch_team(opponent))
```

The pre-fetch runs concurrently with the stat lookup that was already triggered — it only needs to finish before the commentator mentions a player by name, which is usually a few seconds away.

### Cache interaction

`StatsClient._cache` already stores extracted player dicts keyed by `player:{id}`. Pre-fetched entries land in the same cache with the same 45s TTL. No changes needed to the cache layer — the pre-fetch is purely additive.

### Considerations

- **Rate limiting:** the NHL API is public and has no documented rate limit, but firing 8 concurrent player fetches per team detection could be noisy. A small semaphore (e.g. `asyncio.Semaphore(3)`) on the pre-fetch loop keeps it polite.
- **Opponent recursion:** the opponent pre-fetch should not recurse further (don't pre-fetch the opponent's opponent).
- **Scope:** this is a background optimization only. If the pre-fetch hasn't completed when a player is actually mentioned, the normal on-demand fetch path still runs correctly.
