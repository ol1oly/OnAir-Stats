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

---

## User-configurable stat fields per payload type

**Date:** 2026-03-27

Currently the payloads sent over `WS /ws` include a fixed set of fields:

- **Player:** `goals`, `assists`, `points`, `plus_minus`
- **Goalie:** *(not yet defined — implied: `save_pct`, `gaa`, `shutouts`)*
- **Team:** `wins`, `losses`, `ot_losses`, `points`, `goals_for`, `goals_against`

The idea is to let users choose which fields appear on each card type — both which stats to include and in what order.

### Available fields per payload type

The NHL API returns far more than the current fixed selection. A few useful candidates:

| Payload | Available fields |
|---|---|
| **Skater** | `goals`, `assists`, `points`, `plus_minus`, `pim`, `shots`, `shooting_pct`, `toi_per_game`, `power_play_goals`, `power_play_points`, `game_winning_goals` |
| **Goalie** | `save_pct`, `gaa`, `shutouts`, `wins`, `losses`, `ot_losses`, `saves`, `shots_against`, `toi` |
| **Team** | `wins`, `losses`, `ot_losses`, `points`, `goals_for`, `goals_against`, `home_record`, `away_record`, `streak`, `goals_for_per_game`, `goals_against_per_game`, `power_play_pct`, `penalty_kill_pct` |

### Backend implications

`stats.py` would need a per-type field config (loaded from `config.json` or the trigger store) that is applied when constructing the payload before broadcasting. This keeps the NHL API fetch unchanged — fields are just cherry-picked at serialization time.

```python
# example config structure
FIELD_CONFIG = {
    "skater": ["goals", "assists", "points", "toi_per_game"],
    "goalie": ["save_pct", "gaa", "shutouts"],
    "team":   ["wins", "losses", "ot_losses", "points", "power_play_pct"],
}
```

A reasonable default (matching current behavior) ships out of the box so no config is required to run.

### UI implications

This feature touches two distinct UI surfaces:

**1. Settings / config panel (`FieldConfigPanel`)**

A dedicated settings view where the user can, per payload type (skater / goalie / team):
- Toggle fields on/off with checkboxes
- Drag to reorder (the order determines the display order on the card)
- Preview a live mock card as they adjust

This panel writes to a persistent config (e.g. `config.json` via `POST /config/fields`). It does not need to be embedded in the overlay itself — it can live in a separate route (`/settings`) in the React app.

**2. Stat card rendering (`StatCard`, `GoalieCard`, `TeamCard`)**

The cards currently render a hardcoded list of rows. With configurable fields:
- Cards must render dynamically from the `fields` array in the payload (the server pre-applies the config, so the frontend just iterates)
- Label text should be human-readable (e.g. `"toi_per_game"` → `"TOI/GP"`); a frontend label map covers this
- Card height becomes variable — a card with 2 fields is shorter than one with 6. The card container needs a `min-height` and should grow gracefully, or cap at a max row count (4–5 is a reasonable limit for readability at broadcast resolution)
- The slide-in animation and dismiss timer are unaffected

**3. Edge cases to handle**

- If a field is configured but the API returns `null` (e.g. a player with no power-play time), omit that row rather than showing `null` or `0`
- Goalies and skaters are both under `"player"` in the current payload type — the card renderer needs to branch on a `position` or `player_type` field to apply the right field config
- Changing the config mid-broadcast should not affect cards already visible; only new cards pick up the new config
