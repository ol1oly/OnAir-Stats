# NHL Radio Overlay — Architecture Plan

## Stack Decision

| Layer | Choice | Reason |
|---|---|---|
| Audio Capture | Browser MediaRecorder API | No drivers, no Docker device passthrough, works in OBS |
| Transcription | Deepgram WebSocket API | Streaming, ~300ms latency, no GPU needed |
| Entity Extraction | RapidFuzz (active) / Claude API (planned) | Fuzzy n-gram is live; LLM mode defined but not wired |
| Stats | NHL API (nhle.com, no auth) | Authoritative, free, real-time |
| Backend | Python + FastAPI + WebSocket | Async pipeline, easy WS broadcast |
| Frontend | React + Vite | Component-driven overlay, hot reload, fast dev |
| Styling | Tailwind CSS | Utility-first, broadcast-safe dark theme |
| Containerization | Docker + Docker Compose | One-command setup for all users, no local env required |

---

## System Architecture

```
[React Frontend — Vite]
  hooks/
  ├── useMicCapture.ts      — getUserMedia + MediaRecorder, sends audio blobs via WS /audio  ✓
  └── useOverlaySocket.ts   — WS hook, unwraps envelope, parses stat payloads
  components/
  ├── StatCard.tsx          — animated skater stat card
  ├── GoalieCard.tsx        — animated goalie stat card (cyan accent)
  ├── TeamCard.tsx          — animated team stat card
  └── OverlayCanvas.tsx     — manages unified card queue, auto-dismiss (8s)
  types/
  └── payloads.ts           — TypeScript types (PlayerPayload, GoaliePayload, TeamPayload, …)
  main.tsx                  — root, mounts overlay at full 1920×1080
        │
        ▼  WebSocket (ws://localhost:8000/audio) — raw audio blobs
        │
[Python Backend — FastAPI]
  ├── transcriber.py — receives audio blobs, pipes to Deepgram WebSocket            ✓
  ├── extractor.py   — "fuzzy" (active) or "llm" (planned): text → { players, teams }  ✓
  ├── stats.py       — NHL API fetch + 45s in-memory cache; skater/goalie/team        ✓
  └── server.py      — WS /audio (ingest) + WS /ws (broadcast, v1 envelope)          ✓ (pipeline wired)
        │
        ▼  WebSocket (ws://localhost:8000/ws) — { v: 1, payload: StatPayload }
        │
[React Frontend — renders stat cards]

[Docker — planned]
  ├── backend/Dockerfile    — Python 3.11 image, uvicorn entrypoint
  ├── frontend/Dockerfile   — Node 20 builder → nginx static server
  └── docker-compose.yml    — orchestrates backend + frontend, injects .env
```

---

## Data Flow (per audio chunk)

```
1. Browser mic → MediaRecorder (250ms timeslice) → WS /audio → Deepgram → transcript string
2. transcript string → extractor.py (fuzzy or LLM) →
       { "players": ["Connor McDavid"], "teams": ["Edmonton Oilers"] }
3a. Each player name → players.json lookup → player_id
    → NHL API (or cache) → extracted dict (_type: "skater" | "goalie")
    → build_player_payload() or build_goalie_payload()
    → FastAPI broadcast({ v: 1, payload: PlayerPayload | GoaliePayload })
3b. Each team name → teams.json lookup → team_abbrev
    → NHL API standings (or cache) → extracted dict
    → build_team_payload()
    → FastAPI broadcast({ v: 1, payload: TeamPayload })

4. React receives { v: 1, payload } → hook unwraps envelope → OverlayCanvas mounts card → auto-dismisses after 8s
```

### PlayerPayload example

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

### GoaliePayload example

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

### TeamPayload example

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

Full TypeScript types and all payload shapes (including `TriggerPayload` and `SystemPayload`) are documented in [`docs/api/ws-payload-contract.md`](../api/ws-payload-contract.md).

---

## Backend Modules

### `transcriber.py` ✓
- Accepts raw audio blobs from the browser via `WS /audio`
- Pipes blobs to Deepgram WebSocket (no local mic capture or file handling)
- Manages Deepgram WebSocket lifecycle (connect, reconnect, close)
- Fires `on_transcript` callback with final text; only `is_final=True` segments forwarded downstream

### `extractor.py` ✓ (fuzzy mode only)
- **"fuzzy" mode** (active): n-gram generation (1–3 words) from transcript; RapidFuzz `token_sort_ratio` against `players.json` and `teams.json`; two-pass — n-gram then surname partial matching; threshold 82–90 depending on pass
- **"llm" mode** (defined, not wired): one Claude API call per final transcript chunk; returns `{ "players": [...], "teams": [...] }` JSON; LLM call code exists but `EXTRACTOR_MODE=llm` path is not connected in server.py
- Returns: `{ "players": List[str], "teams": List[str] }` with canonical names; falls back to empty lists on any failure

### `stats.py` ✓
- `players.json`: `{ "Connor McDavid": 8478402, ... }` (~50 seeded players)
- `teams.json`: `{ "Edmonton Oilers": "EDM", "Oilers": "EDM", ... }` (all 32 teams + common aliases)
- **Player fetch**: `GET https://api-web.nhle.com/v1/player/{id}/landing`
  - Detects goalie via `positionCode == "G"`, returns extracted dict with `_type: "skater" | "goalie"`
  - Skater fields: `goals`, `assists`, `points`, `plus_minus`
  - Goalie fields: `wins`, `losses`, `ot_losses`, `save_percentage`, `goals_against_avg`, `shutouts`
- **Team fetch**: `GET https://api-web.nhle.com/v1/standings/now`
  - Filters by team abbreviation; includes `conference_rank`, `division_rank`, `point_pct`, `logo_url`
  - Entire 32-team response cached as single key `"standings"` (TTL 45s)
- Cache: `dict[str, (timestamp, dict)]` — TTL 45s, keyed by `f"player:{player_id}"` or `"standings"`
- Payload builders: `build_player_payload()`, `build_goalie_payload()`, `build_team_payload()`

### `server.py` ✓
- FastAPI app
- `GET /` → serves React build (static files from `frontend/dist`)
- `WS /audio` → receives raw audio blobs, pipes to `transcriber.py`
- `WS /ws` → accepts browser connections, broadcasts stat JSON
- `broadcast(payload: dict)` → wraps in `{ "v": 1, "payload": payload }` envelope, sends to all `/ws` clients, silently removes disconnected clients
- Full async pipeline wired: transcript → `extract_entities()` → stats lookups → `build_*_payload()` → `broadcast()`
- `SystemPayload` events emitted on: overlay client connect/disconnect, Deepgram ready, Deepgram error

---

## Frontend Modules (React + Vite)

### `hooks/useMicCapture.ts` ✓
- Calls `navigator.mediaDevices.getUserMedia({ audio: true })` on `start()`
- Uses `MediaRecorder` with ~250ms `timeslice` (batching interval only — Deepgram determines utterance boundaries via `is_final`)
- Sends each blob as binary over `WS /audio`
- Exposes `{ start(), stop(), isRecording, isConnected }`
- Works natively in OBS browser sources (requires "Allow Audio Capture" enabled on the browser source)

### `hooks/useOverlaySocket.ts`
- Connects to `ws://localhost:8000/ws` on mount
- **Envelope unwrap:** every message is `{ v: 1, payload: ... }` — the hook strips the envelope
- Discriminates on `payload.type`: stat payloads → `latestPayload`; `"system"` → `systemEvent`
- Auto-reconnects on disconnect (exponential backoff: 1s, 2s, 4s, capped at 5s)
- Returns `{ latestPayload: StatPayload | null, systemEvent: SystemPayload | null, isConnected: boolean }`

### `types/payloads.ts`
- TypeScript types copied from `docs/api/ws-payload-contract.md`
- Exports: `PlayerPayload`, `GoaliePayload`, `TeamPayload`, `TriggerPayload`, `SystemPayload`, `StatPayload`, `Envelope`

### `components/StatCard.tsx`
- Props: `payload: PlayerPayload`, `onExpire: () => void`
- Animates in (slide from left + fade, 0.3s ease-out), auto-dismisses after 8s
- Colors: goals `text-red-500`, assists `text-blue-500`, points `text-white`, plus/minus conditional green/red
- Renders from individual `stats` fields for color coding (not from `display` string)

### `components/GoalieCard.tsx`
- Props: `payload: GoaliePayload`, `onExpire: () => void`
- Same animation and auto-dismiss as StatCard
- Cyan/teal accent (`text-cyan-400`) throughout to distinguish from skater cards
- Stats: save percentage (no leading zero: `.907`), GAA, shutouts, W–L–OT record

### `components/TeamCard.tsx`
- Props: `payload: TeamPayload`, `onExpire: () => void`
- Same animation and dismiss behaviour as StatCard
- Team abbreviation large and bold in gold/amber (`text-amber-400`); record in W–L–OT format, points total, conference/division rank
- `logo_url` available for future team logo display

### `components/OverlayCanvas.tsx`
- Holds card queue `Array<{ id: string, payload: StatPayload }>` in state
- `id` generated as `${type}_${payload.id || payload.abbrev}_${payload.ts}`
- Uses `useOverlaySocket`; routes by `payload.type`: `"player"` → `<StatCard>`, `"goalie"` → `<GoalieCard>`, `"team"` → `<TeamCard>`, `"system"` → status flag only (no card)
- Deduplicates same entity within 2s window; max 3 cards visible (drops oldest)
- Positioned bottom-left, stacks vertically: `absolute bottom-8 left-8 flex flex-col-reverse gap-3`
- Handles card lifecycle (add on new payload, remove on `onExpire`)

### `main.tsx`
- Transparent background (`bg-transparent`) for OBS browser source
- Full 1920×1080 canvas: `w-screen h-screen bg-transparent overflow-hidden relative`
- Mounts `OverlayCanvas` only — no router, no navigation

---

## Docker Architecture

### `backend/Dockerfile`
- Base image: `python:3.11-slim`
- No system audio dependencies needed (mic runs in browser)
- Copies `backend/` source, installs `requirements.txt`
- Exposes port `8000`
- Entrypoint: `uvicorn server:app --host 0.0.0.0 --port 8000`
- Pre-built React `dist/` copied in or mounted as a volume

### `frontend/Dockerfile`
- **Stage 1 — builder**: `node:20-alpine` — runs `npm ci && npm run build`, outputs `dist/`
- **Stage 2 — server**: `nginx:alpine` — copies `dist/` into nginx web root, exposes port `80`

### `docker-compose.yml`
- **`backend` service**: builds from `backend/Dockerfile`, exposes `8000:8000`, loads secrets via `env_file: .env`
- **`frontend` service** (optional, `--profile full`): builds from `frontend/Dockerfile`, exposes `5173:80`
- Default (no profile): only `backend` runs — FastAPI serves the React build at `GET /`
- No mic device passthrough needed — audio captured in browser over WebSocket
- `.env` injected at runtime, never baked into images

### Running the app

```bash
# 1. Fill in your API keys
cp .env.example .env

# 2. Build and start (single container — backend serves frontend too)
docker compose up --build

# 3. Open OBS Browser Source at http://localhost:8000
#    Or open http://localhost:8000 in any browser to preview
```

---

## Latency Budget

| Step | Target |
|---|---|
| Deepgram transcription | ~300ms |
| Fuzzy extraction (RapidFuzz) | ~5ms |
| LLM extraction (Claude, when enabled) | ~500ms |
| NHL API player (uncached) | ~200ms |
| NHL API standings/team (uncached) | ~200ms |
| NHL API (cached) | ~5ms |
| WS broadcast + React render | ~50ms |
| **Total fuzzy (cold cache)** | **~755ms ✅** |
| **Total fuzzy (warm cache)** | **~360ms ✅** |
| **Total LLM (cold cache)** | **~1,250ms ✅** |

---

## Repo Structure

```
radio-nhl-overlay/
├── backend/
│   ├── transcriber.py
│   ├── extractor.py
│   ├── stats.py
│   ├── server.py
│   ├── players.json
│   ├── teams.json
│   ├── requirements.txt
│   ├── tests/
│   │   ├── test_stats.py
│   │   └── test_extractor.py
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── main.tsx
│   │   ├── index.css           ← shared card-enter / card-exit keyframes
│   │   ├── types/
│   │   │   └── payloads.ts
│   │   ├── hooks/
│   │   │   ├── useMicCapture.ts
│   │   │   └── useOverlaySocket.ts
│   │   └── components/
│   │       ├── OverlayCanvas.tsx
│   │       ├── StatCard.tsx
│   │       ├── GoalieCard.tsx
│   │       └── TeamCard.tsx
│   ├── index.html
│   ├── vite.config.ts
│   ├── tailwind.config.ts
│   ├── package.json
│   └── Dockerfile
├── docs/
│   ├── api/
│   │   └── ws-payload-contract.md
│   ├── project/
│   │   ├── plan.md
│   │   └── task.md
│   ├── frontend-design.md
│   └── notes.md
├── docker-compose.yml
├── .env.example
├── .env              ← gitignored
└── README.md
```

---

## Environment Variables (`.env`)

```
DEEPGRAM_API_KEY=your_key_here
ANTHROPIC_API_KEY=your_key_here
GEMINI_API_KEY=your_key_here
EXTRACTOR_MODE=fuzzy    # "fuzzy" (active) or "llm" (planned)
```

Both `DEEPGRAM_API_KEY` and `ANTHROPIC_API_KEY` are passed into the `backend` container via `env_file`. The frontend has no secrets.

---

## Post-MVP

### LLM Extractor
`extractor.py` has the LLM extraction code defined but `EXTRACTOR_MODE=llm` is not wired in `server.py`. Enabling it requires connecting the mode toggle in the server's `_on_transcript` handler and verifying the Claude/Gemini API path end-to-end.

### Custom Triggers
User-defined keyword→NHL API mappings. See `docs/project/trigger-builder.md` (planned).
- Backend: `trigger_resolver.py`, `trigger_store.py`, `trigger_runner.py`
- Frontend: `TriggerCard.tsx`, `TriggerBuilder.tsx`, `TriggerList.tsx` on a `/settings` route
- `OverlayCanvas` already routes `"trigger"` type (one `case` to add)

### Keyword-Based Action Extraction
Add an `actions` field to `extract_entities` output by detecting hockey-action keywords (e.g. `scores` → `"scoring"`, `penalty` → `"penalty"`). Simple set-based keyword lookup, no fuzzy matching needed. Enables the server to prioritize which stat card to show and eventually filter low-signal mentions. See `docs/notes.md` for keyword groups and pipeline sketch.

### Background Roster Pre-fetch
When a team is detected, fire-and-forget pre-fetch key players (captains, top forwards, starting goalie) into the cache via `GET /v1/roster/{abbrev}/current`. Also fetch today's opponent via the schedule endpoint. Uses a `Semaphore(3)` to stay polite. No cache layer changes — pre-fetched entries share the same `player:{id}` keys and TTL. See `docs/notes.md` for full pipeline sketch.

### User-Configurable Stat Fields
Let users toggle and reorder which fields appear on each card type via a `FieldConfigPanel` on `/settings`. Backend applies the config at serialization time (`FIELD_CONFIG` dict in `stats.py`); frontend iterates a `fields` array instead of hardcoded rows. Default config matches current behavior — no config required to run. See `docs/notes.md` for full backend/UI breakdown.

### Team Logo Images
`logo_url` is already included in `TeamPayload` (constructed from `abbrev`: `.../svg/{abbrev}_light.svg`). Just needs to be rendered in `TeamCard`.

### OBS Integration Reference

| Setting | Value |
|---|---|
| URL | `http://localhost:8000` |
| Resolution | 1920 × 1080 |
| Background | Transparent |
| Audio capture | Enable "Allow Audio Capture" on the browser source |
