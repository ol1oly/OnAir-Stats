# NHL Radio Overlay — Architecture Plan

## Stack Decision

| Layer | Choice | Reason |
|---|---|---|
| Audio Capture | Browser MediaRecorder API | No drivers, no Docker device passthrough, works in OBS |
| Transcription | Deepgram WebSocket API | Streaming, ~300ms latency, no GPU needed |
| Entity Extraction | Claude API (Anthropic) | Accurate player **and team** name extraction per chunk |
| Stats | NHL API (nhle.com, no auth) | Authoritative, free, real-time |
| Backend | Python + FastAPI + WebSocket | Async pipeline, easy WS broadcast |
| Frontend | React + Vite | Component-driven overlay, hot reload, fast dev |
| Styling | Tailwind CSS | Utility-first, broadcast-safe dark theme |
| Containerization | Docker + Docker Compose | One-command setup for all users, no local env required |

---

## System Architecture

```
[React Frontend — Vite]
  ├── useMicCapture.ts      — getUserMedia + MediaRecorder, sends audio blobs via WS /audio
  ├── useOverlaySocket.ts   — WS hook, parses incoming stat payloads
  ├── StatCard.tsx          — animated player stat card
  ├── TeamCard.tsx          — animated team stat card
  ├── OverlayCanvas.tsx     — manages unified card queue, auto-dismiss (8s)
  └── main.tsx              — root, mounts overlay at full 1920×1080
        │
        ▼  WebSocket (ws://localhost:8000/audio) — raw audio blobs
        │
[Python Backend — FastAPI]
  ├── transcriber.py — receives audio blobs, pipes to Deepgram WebSocket
  ├── extractor.py   — Claude API: text → { players: [...], teams: [...] }
  ├── stats.py       — NHL API fetch + 45s in-memory cache (players + teams)
  └── server.py      — FastAPI; WS /audio (ingest) + WS /ws (stat broadcast)
        │
        ▼  WebSocket (ws://localhost:8000/ws) — stat JSON payloads
        │
[React Frontend — receives stat cards]

[Docker]
  ├── backend/Dockerfile    — Python 3.11 image, uvicorn entrypoint
  ├── frontend/Dockerfile   — Node 20 builder → nginx static server
  └── docker-compose.yml    — orchestrates backend + frontend, injects .env
                              (no mic device passthrough needed)
```

---

## Data Flow (per audio chunk)

```
1. Browser mic → MediaRecorder (3–4s blobs) → WS /audio → Deepgram → transcript string
2. transcript string → Claude API →
       { "players": ["Connor McDavid"], "teams": ["Edmonton Oilers"] }
3a. Each player name → players.json lookup → player_id
    → NHL API (or cache) → { goals, assists, points, plus_minus }
    → FastAPI broadcasts PlayerPayload JSON
3b. Each team name → teams.json lookup → team_abbrev
    → NHL API standings (or cache) → { wins, losses, ot_losses, points, goals_for, goals_against }
    → FastAPI broadcasts TeamPayload JSON

PlayerPayload example:
{
  "type": "player",
  "player": "Connor McDavid",
  "stats": {
    "goals": 32,
    "assists": 100,
    "points": 132,
    "plus_minus": 15
  },
  "display": "McDavid · 32G  100A  132PTS  +15"
}

TeamPayload example:
{
  "type": "team",
  "team": "Edmonton Oilers",
  "abbrev": "EDM",
  "stats": {
    "wins": 42,
    "losses": 20,
    "ot_losses": 5,
    "points": 89,
    "goals_for": 198,
    "goals_against": 167
  },
  "display": "EDM · 42W  20L  5OT  89PTS"
}

4. React receives message → mounts StatCard or TeamCard → auto-dismisses after 8s
```

---

## Backend Modules

### `transcriber.py`
- Accepts raw audio blobs from the browser via `WS /audio`
- Pipes blobs to Deepgram WebSocket (no local mic capture or file handling)
- Manages Deepgram WebSocket lifecycle (connect, reconnect, close)
- Fires `on_transcript` callback with final text; only `is_final=True` segments forwarded downstream

### `extractor.py`
- Mode toggle: choose between `"llm"` (Claude) or `"fuzzy"` (RapidFuzz) extraction
- **"llm" mode**: One Claude API call per final transcript chunk
  - System prompt: extract NHL player names AND team names, return structured JSON `{ "players": [...], "teams": [...] }`, never infer
- **"fuzzy" mode**: No API calls; uses n-gram extraction + RapidFuzz to detect and normalize misspelled or partial names/aliases against both `players.json` and `teams.json` (including common short forms like "the Oilers" → "Edmonton Oilers")
- Returns: `{ "players": List[str], "teams": List[str] }`
- Falls back to `{ "players": [], "teams": [] }` on any failure

### `stats.py`
- `players.json`: `{ "Connor McDavid": 8478402, ... }` (~50 seeded players)
- `teams.json`: `{ "Edmonton Oilers": "EDM", "Toronto Maple Leafs": "TOR", ... }` (all 32 teams, includes common aliases like `"Oilers": "EDM"`)
- **Player fetch**: `GET https://api-web.nhle.com/v1/player/{id}/landing`
  - Extracts `{ goals, assists, points, plus_minus }` from current season stats
- **Team fetch**: `GET https://api-web.nhle.com/v1/standings/now`
  - Filters by team abbreviation → `{ wins, losses, ot_losses, points, goals_for, goals_against }`
  - Standings response covers all 32 teams; cached as a single global entry (TTL 45s)
- Cache: `dict[str, (timestamp, dict)]` — TTL 45 seconds, keyed by player_id or team abbreviation
- Returns structured stats dict or `None` if entity not found

### `server.py`
- FastAPI app
- `GET /` → serves React build (static files from `frontend/dist`)
- `WS /audio` → receives raw audio blobs from the browser mic, pipes to `transcriber.py`
- `WS /ws` → accepts browser connections, broadcasts stat JSON
- Async pipeline: `browser mic → /audio → transcriber → extractor → stats → broadcast /ws`
- Broadcasts both `PlayerPayload` and `TeamPayload` objects; each carries a `"type"` discriminator field (`"player"` or `"team"`)

---

## Frontend Modules (React + Vite)

### `useMicCapture.ts`
- Calls `navigator.mediaDevices.getUserMedia({ audio: true })` to request mic access
- Uses `MediaRecorder` to capture audio in ~3s blobs
- Sends each blob as binary data over `WS /audio` to the backend
- Exposes `{ start(), stop(), isRecording, isConnected }`
- Works natively in OBS browser sources (OBS grants mic access when "Access to OBS virtual camera" is enabled)

### `useOverlaySocket.ts`
- Connects to `ws://localhost:8000/ws`
- Auto-reconnects on disconnect (exponential backoff, max 5s)
- Parses incoming JSON as `PlayerPayload | TeamPayload`, discriminated by `type` field
- Returns `{ latestPayload: StatPayload | null, isConnected: boolean }`

### `StatCard.tsx`
- Props: `payload: PlayerPayload`, `onExpire: () => void`
- Animates in (slide + fade), auto-dismisses after 8s
- Broadcast-safe design: dark background, large readable type
- Colors: goals red, assists blue, points white, plus/minus conditional green/red

### `TeamCard.tsx`
- Props: `payload: TeamPayload`, `onExpire: () => void`
- Same animation and dismiss behaviour as `StatCard`
- Displays team abbreviation prominently, record in W–L–OT format, points total
- Accent color: gold/yellow to visually distinguish from player cards at a glance

### `OverlayCanvas.tsx`
- Manages a unified queue of active `StatCard` and `TeamCard` components (max 3 visible)
- Routes each incoming payload to the correct card component via the `type` field
- Positioned bottom-left, stacks vertically
- Handles card lifecycle (add, expire, remove)
- Deduplicates same entity within a 2s window to avoid flicker on repeated mentions

### `main.tsx`
- Transparent background (`bg-transparent`) for OBS browser source
- Full 1920×1080 canvas
- Mounts `OverlayCanvas`

---

## Docker Architecture

### `backend/Dockerfile`
- Base image: `python:3.11-slim`
- No system audio dependencies needed (mic runs in browser)
- Copies `backend/` source, installs `requirements.txt`
- Exposes port `8000`
- Entrypoint: `uvicorn server:app --host 0.0.0.0 --port 8000`
- Serves pre-built React `dist/` as static files (copied in during build or mounted as a volume)

### `frontend/Dockerfile`
- **Stage 1 — builder**: `node:20-alpine` — runs `npm ci && npm run build`, outputs `dist/`
- **Stage 2 — server**: `nginx:alpine` — copies `dist/` into nginx web root, exposes port `80`
- Used when running the frontend as a standalone nginx service (optional; see below)

### `docker-compose.yml`
- **`backend` service**: builds from `backend/Dockerfile`, exposes `8000:8000`, loads secrets via `env_file: .env`
- **`frontend` service** (optional, `--profile full`): builds from `frontend/Dockerfile`, exposes `5173:80`; useful for development or when decoupling frontend/backend deployments
- Default (no profile): only `backend` runs — FastAPI serves the React build at `GET /`, so a single container is sufficient for OBS use
- No mic device passthrough needed — audio is captured in the browser and sent to the backend over WebSocket
- `.env` is never baked into images; it is injected at `docker run` / `docker compose up` time

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
| Claude extraction (players + teams) | ~500ms |
| NHL API player (uncached) | ~200ms |
| NHL API standings/team (uncached) | ~200ms |
| NHL API (cached) | ~5ms |
| WS broadcast + React render | ~50ms |
| **Total (cold)** | **~1,050ms ✅** |
| **Total (warm cache)** | **~855ms ✅** |

---

## Repo Structure

```
radio-nhl-overlay/
├── backend/
│   ├── main.py
│   ├── transcriber.py
│   ├── extractor.py
│   ├── stats.py
│   ├── server.py
│   ├── players.json
│   ├── teams.json
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── main.tsx
│   │   ├── OverlayCanvas.tsx
│   │   ├── StatCard.tsx
│   │   ├── TeamCard.tsx
│   │   ├── useMicCapture.ts
│   │   └── useOverlaySocket.ts
│   ├── index.html
│   ├── vite.config.ts
│   ├── tailwind.config.ts
│   ├── package.json
│   └── Dockerfile
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
```

Both variables are passed into the `backend` container via `env_file` in `docker-compose.yml`. The frontend has no secrets and requires no environment variables.

---

## Out of Scope (MVP)

- Authentication or multi-user support
- LLM-generated stats (all numbers from NHL API only)
- Persistent storage or database
- Team logo images in overlay cards (text-only MVP)
