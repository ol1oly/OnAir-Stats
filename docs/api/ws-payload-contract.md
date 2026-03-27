# WebSocket Payload Contract — Backend → Frontend

This document defines the data shapes the frontend receives over `WS /ws`. It is the single source of truth for what the overlay renders — the frontend must never parse raw NHL API responses directly.

---

## Overview

All messages are JSON objects wrapped in a versioned envelope. The `payload.type` discriminator tells the frontend which card component to render.

```typescript
type Envelope = {
  v:       1           // schema version — increment when the payload shape changes
  payload: StatPayload
}

type StatPayload = PlayerPayload | GoaliePayload | TeamPayload | TriggerPayload | SystemPayload
```

Each payload carries only the fields needed to render a card, plus a `ts` timestamp for dedup and latency tracking. Raw NHL API responses (which can be several KB with deeply nested objects) are reduced to a flat, typed structure before broadcast.

---

## 1. `PlayerPayload`

Triggered when a skater's name is detected in the transcript.

### Shape

```typescript
type PlayerPayload = {
  type: "player"

  // Identity
  id:           number   // NHL player ID — stable, use as React key
  name:         string   // "Connor McDavid"
  team:         string   // "EDM"
  position:     string   // "C" | "LW" | "RW" | "D"
  headshot_url: string   // "https://assets.nhle.com/mugs/nhl/skater/8478402.png"

  // Season stats
  stats: {
    season:       string   // "20242025"
    games_played: number
    goals:        number
    assists:      number
    points:       number
    plus_minus:   number
  }

  // Pre-formatted one-liner for the card header
  display: string   // "McDavid · 32G  100A  132PTS  +15"

  ts: number   // Unix ms — when this payload was assembled on the backend
}
```

### Example

```json
{
  "v": 1,
  "payload": {
    "type": "player",
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
      "plus_minus": 15
    },
    "display": "McDavid · 32G  100A  132PTS  +15",
    "ts": 1743098400000
  }
}
```

### Mapped from NHL API

`GET /v1/player/{id}/landing`

| Payload field        | NHL API path                                             |
|----------------------|----------------------------------------------------------|
| `id`                 | `playerId`                                               |
| `name`               | `firstName.default` + `lastName.default`                 |
| `team`               | `currentTeamAbbrev`                                      |
| `position`           | `position`                                               |
| `headshot_url`       | `headshot` (direct URL in response)                      |
| `stats.season`       | `featuredStats.season` (number → string, e.g. `20242025`)|
| `stats.games_played` | `featuredStats.regularSeason.subSeason.gamesPlayed`      |
| `stats.goals`        | `featuredStats.regularSeason.subSeason.goals`            |
| `stats.assists`      | `featuredStats.regularSeason.subSeason.assists`          |
| `stats.points`       | `featuredStats.regularSeason.subSeason.points`           |
| `stats.plus_minus`   | `featuredStats.regularSeason.subSeason.plusMinus`        |

**Intentionally excluded:** `birthDate`, `birthCity`, `height`, `weight`, `draftDetails`, `awards`, all career stats, all previous season stats.

---

## 2. `GoaliePayload`

Separate type for goaltenders — skater stats are meaningless for goalies.

### Shape

```typescript
type GoaliePayload = {
  type: "goalie"

  // Identity
  id:           number
  name:         string
  team:         string
  headshot_url: string   // "https://assets.nhle.com/mugs/nhl/skater/8474593.png"

  // Season stats
  stats: {
    season:            string
    games_played:      number
    wins:              number
    losses:            number
    ot_losses:         number
    save_percentage:   number   // e.g. 0.912
    goals_against_avg: number   // e.g. 2.45
    shutouts:          number
  }

  display: string   // "Markstrom · .912 SV%  2.45 GAA  4 SO"

  ts: number
}
```

### Example

```json
{
  "v": 1,
  "payload": {
    "type": "goalie",
    "id": 8474593,
    "name": "Jacob Markstrom",
    "team": "NJD",
    "headshot_url": "https://assets.nhle.com/mugs/nhl/skater/8474593.png",
    "stats": {
      "season": "20242025",
      "games_played": 48,
      "wins": 22,
      "losses": 19,
      "ot_losses": 4,
      "save_percentage": 0.907,
      "goals_against_avg": 2.98,
      "shutouts": 2
    },
    "display": "Markstrom · .907 SV%  2.98 GAA  2 SO",
    "ts": 1743098400000
  }
}
```

### Mapped from NHL API

Same endpoint as skaters: `GET /v1/player/{id}/landing`

| Payload field             | NHL API path                                            |
|---------------------------|---------------------------------------------------------|
| `headshot_url`            | `headshot`                                              |
| `stats.season`            | `featuredStats.season`                                  |
| `stats.wins`              | `featuredStats.regularSeason.subSeason.wins`            |
| `stats.losses`            | `featuredStats.regularSeason.subSeason.losses`          |
| `stats.ot_losses`         | `featuredStats.regularSeason.subSeason.otLosses`        |
| `stats.save_percentage`   | `featuredStats.regularSeason.subSeason.savePctg`        |
| `stats.goals_against_avg` | `featuredStats.regularSeason.subSeason.goalsAgainstAvg` |
| `stats.shutouts`          | `featuredStats.regularSeason.subSeason.shutouts`        |

> **Detection:** the backend checks `positionCode === "G"` on the player landing response and routes to `GoaliePayload` instead of `PlayerPayload`.

---

## 3. `TeamPayload`

Triggered when a team name or alias is detected in the transcript. Shows the team's current season standings record.

### Shape

```typescript
type TeamPayload = {
  type: "team"

  // Identity
  name:     string   // "Edmonton Oilers"
  abbrev:   string   // "EDM"
  logo_url: string   // "https://assets.nhle.com/logos/nhl/svg/EDM_light.svg"

  // Current standings (season is always the current season for standings/now)
  stats: {
    season:        string   // "20242025"
    wins:          number
    losses:        number
    ot_losses:     number
    points:        number
    games_played:  number
    goals_for:     number
    goals_against: number
    point_pct:     number   // e.g. 0.664
  }

  // Placement
  conference_rank: number   // rank within conference
  division_rank:   number   // rank within division

  display: string   // "EDM · 42W  20L  5OT  89PTS"

  ts: number
}
```

### Example

```json
{
  "v": 1,
  "payload": {
    "type": "team",
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
      "point_pct": 0.664
    },
    "conference_rank": 3,
    "division_rank": 2,
    "display": "EDM · 42W  20L  5OT  89PTS",
    "ts": 1743098400000
  }
}
```

### Mapped from NHL API

`GET /v1/standings/now` — single request returns all 32 teams. Filter by `teamAbbrev`. The `logo_url` is constructed from `abbrev` — no extra API call needed.

| Payload field         | NHL API path (per team entry)                  |
|-----------------------|------------------------------------------------|
| `name`                | `teamName.default`                             |
| `abbrev`              | `teamAbbrev`                                   |
| `logo_url`            | constructed: `.../svg/{teamAbbrev}_light.svg`  |
| `stats.season`        | `season` (top-level response field)            |
| `stats.wins`          | `wins`                                         |
| `stats.losses`        | `losses`                                       |
| `stats.ot_losses`     | `otLosses`                                     |
| `stats.points`        | `points`                                       |
| `stats.games_played`  | `gamesPlayed`                                  |
| `stats.goals_for`     | `goalFor`                                      |
| `stats.goals_against` | `goalAgainst`                                  |
| `stats.point_pct`     | `pointPctg`                                    |
| `conference_rank`     | `conferenceSequence`                           |
| `division_rank`       | `divisionSequence`                             |

**Intentionally excluded:** `wildcardSequence`, `leagueSequence`, `streakCode`, `lastTenWins`, `homeWins`, `roadWins`, `l10Wins`, conference/division name strings (derivable from `abbrev`).

---

## 4. `TriggerPayload`

Triggered when a custom trigger keyword is fuzzy-matched in the transcript. Shape is dynamic — the `fields` array varies per trigger definition.

### Shape

```typescript
type TriggerField = {
  label: string   // "PP Goals"
  value: string | number | null
}

type TriggerPayload = {
  type:        "trigger"
  id:          string          // trigger UUID — stable, use as React key
  keywords:    string[]        // ["power play"]
  description: string          // user's original intent
  fields:      TriggerField[]  // resolved label/value pairs
  display:     string          // "power play · PP Goals: 24"

  ts: number
}
```

### Example

```json
{
  "v": 1,
  "payload": {
    "type": "trigger",
    "id": "a3f2c1b0-...",
    "keywords": ["power play"],
    "description": "Show how many power play goals the Oilers have scored",
    "fields": [
      { "label": "PP Goals",   "value": 24 },
      { "label": "First Name", "value": "Connor" },
      { "label": "Last Name",  "value": "McDavid" }
    ],
    "display": "power play · PP Goals: 24",
    "ts": 1743098400000
  }
}
```

> **Note:** Triggers are intentionally separate from `TeamPayload`. A trigger is user-defined, fires on arbitrary keywords, and can fetch any NHL API endpoint — including standings data for a specific team. `TeamPayload` is auto-triggered by the entity extractor and always shows the same standing fields. Both can coexist in the overlay at the same time.

---

## 5. `SystemPayload`

A lightweight envelope for backend status events that the overlay UI can react to. No stat card is rendered — this feeds a status indicator or debug panel.

### Shape

```typescript
type SystemPayload = {
  type:    "system"
  event:   "connected" | "disconnected" | "transcriber_ready" | "transcriber_error"
  message: string   // human-readable detail for dev/debug display
  ts:      number
}
```

### Events

| Event               | When it fires                                               |
|---------------------|-------------------------------------------------------------|
| `connected`         | A new overlay client connects to `WS /ws`                  |
| `disconnected`      | The overlay client disconnects                             |
| `transcriber_ready` | Deepgram WebSocket connection is established               |
| `transcriber_error` | Deepgram connection fails or the API key is invalid        |

### Why

The frontend has no way to tell a user why no cards are appearing (wrong API key? Deepgram down? Mic not captured?). `SystemPayload` lets the overlay surface this without coupling it to stat card rendering.

---

## Future Consideration

### `StandingsPayload` for multi-team tables

`TeamPayload` shows a single team's record and is the right shape for a single audio-triggered card. If the overlay ever needs to render a full division or conference standings table (e.g., triggered by "who's leading the Pacific?"), a separate type would be appropriate:

```typescript
type StandingsPayload = {
  type:      "standings"
  scope:     "division" | "conference" | "league"
  scope_name: string              // "Pacific", "Western", "NHL"
  season:    string
  teams:     Array<{
    rank:         number
    abbrev:       string
    logo_url:     string
    points:       number
    wins:         number
    losses:       number
    ot_losses:    number
    point_pct:    number
  }>
}
```

This would require a dedicated trigger or a new entity extraction intent — out of scope for MVP.

---

## TypeScript Types

Copy into `useOverlaySocket.ts` once the components are built.

```typescript
export type PlayerPayload = {
  type: "player"
  id: number
  name: string
  team: string
  position: string
  headshot_url: string
  stats: {
    season: string
    games_played: number
    goals: number
    assists: number
    points: number
    plus_minus: number
  }
  display: string
  ts: number
}

export type GoaliePayload = {
  type: "goalie"
  id: number
  name: string
  team: string
  headshot_url: string
  stats: {
    season: string
    games_played: number
    wins: number
    losses: number
    ot_losses: number
    save_percentage: number
    goals_against_avg: number
    shutouts: number
  }
  display: string
  ts: number
}

export type TeamPayload = {
  type: "team"
  name: string
  abbrev: string
  logo_url: string
  stats: {
    season: string
    wins: number
    losses: number
    ot_losses: number
    points: number
    games_played: number
    goals_for: number
    goals_against: number
    point_pct: number
  }
  conference_rank: number
  division_rank: number
  display: string
  ts: number
}

export type TriggerPayload = {
  type: "trigger"
  id: string
  keywords: string[]
  description: string
  fields: { label: string; value: string | number | null }[]
  display: string
  ts: number
}

export type SystemPayload = {
  type: "system"
  event: "connected" | "disconnected" | "transcriber_ready" | "transcriber_error"
  message: string
  ts: number
}

export type StatPayload = PlayerPayload | GoaliePayload | TeamPayload | TriggerPayload | SystemPayload

export type Envelope = {
  v: 1
  payload: StatPayload
}
```
