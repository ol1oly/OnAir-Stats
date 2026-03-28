# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**NHL Radio Overlay** — a live broadcast overlay that listens to NHL radio commentary, transcribes it in real-time, extracts player/team names, fetches live stats from the NHL API, and displays animated stat cards in a browser source for OBS.

## Current Implementation State

The project is in active development. Backend pipeline stub is wired; frontend overlay components and hooks are built but the backend `_on_transcript()` pipeline is not yet connected.

**Implemented:**
- `backend/transcriber.py` — Deepgram WebSocket streaming transcriber
- `backend/extractor.py` — Fuzzy entity extraction (RapidFuzz n-gram); LLM mode partially wired
- `backend/stats.py` — `StatsClient` with 45s in-memory cache; `get_player()` (skater + goalie) and `get_team()` (standings) fully implemented
- `backend/server.py` — FastAPI app; `_on_transcript()` is still a stub (pipeline not yet wired)
- `frontend/src/components/` — `OverlayCanvas`, `StatCard`, `GoalieCard`, `TeamCard` (all built with Tailwind + slide-in animations)
- `frontend/src/hooks/` — `useOverlaySocket.ts` (WS hook with auto-reconnect), `useMicCapture.ts` (getUserMedia + MediaRecorder)
- `frontend/src/types/payloads.ts` — full TypeScript payload types for all message shapes
- Tests: `backend/tests/` (pytest) and `frontend/src/components/__tests__/` + `frontend/src/hooks/__tests__/` (Vitest + Testing Library)

**Not yet built:** Docker / `docker-compose.yml`, `main.py`, trigger system (`trigger_resolver.py`, `trigger_store.py`, `trigger_runner.py`), `TriggerCard.tsx`, `TriggerBuilder.tsx`, `TriggerList.tsx`, mic control UI (MIC-02), backend `_on_transcript()` pipeline wiring.

## Development

**Backend:**

The backend uses a virtual environment at `backend/.venv`. Always use it explicitly — never the system Python.

```bash
cd backend
backend/.venv/Scripts/python.exe -m pip install -r requirements.txt
backend/.venv/Scripts/python.exe -m uvicorn server:app --reload --port 8000
```

Run tests:
```bash
backend/.venv/Scripts/python.exe -m pytest tests/
backend/.venv/Scripts/python.exe -m pytest tests/test_server.py -v
```

### Python Dependencies
When installing any Python package:
- Use `backend/.venv/Scripts/python.exe -m pip install <package>`
- Add the package and its version to requirements.txt manually (e.g. `requests==2.31.0`)
- Do not use `pip freeze` as it captures indirect dependencies — only add the package you explicitly installed

**Frontend:**
```bash
cd frontend
npm install
npm run dev       # dev server at http://localhost:5173
npm run build     # outputs dist/ (required before serving from backend)
npm run lint
npm run test      # Vitest (jsdom environment)
```

**Tests:**
```bash
# Backend
backend/.venv/Scripts/python.exe -m pytest tests/
backend/.venv/Scripts/python.exe -m pytest tests/test_stats.py -v

# Frontend (from frontend/)
npm run test
```

**Standalone module tests (no server needed):**
```bash
# Test extractor against sample sentences
backend/.venv/Scripts/python.exe backend/extractor.py "McDavid scores against the Maple Leafs"

# Test transcriber against an audio file or mic
backend/.venv/Scripts/python.exe backend/transcriber.py sample.mp3
backend/.venv/Scripts/python.exe backend/transcriber.py --mic
```

## Environment Variables (`.env`)

```
DEEPGRAM_API_KEY=
ANTHROPIC_API_KEY=
GEMINI_API_KEY=
EXTRACTOR_MODE=llm    # "llm" or "fuzzy"
```

## Architecture

Audio is captured in the browser (no mic drivers or Docker device passthrough needed) and streamed to the backend over WebSocket.

```
Browser mic (getUserMedia + MediaRecorder)
→ WS /audio (binary blobs) → transcriber.py → Deepgram WebSocket → transcript
→ extractor.py (LLM or fuzzy) → { players, teams }
→ stats.py (NHL API + 45s cache) → PlayerPayload / TeamPayload
→ FastAPI WS /ws → React OverlayCanvas → StatCard / TeamCard
```

### Backend (`backend/`)

| File | Role |
|---|---|
| `main.py` | *(planned)* Entry point; wires transcriber → extractor → stats → broadcast |
| `transcriber.py` | Receives audio blobs from `WS /audio`, pipes to Deepgram; fires `on_transcript` for final segments only |
| `extractor.py` | Dual-mode: `"llm"` (Claude/Gemini) or `"fuzzy"` (RapidFuzz n-gram). Returns `{ players: [], teams: [] }` |
| `stats.py` | NHL API fetches with 45s in-memory cache. `players.json` maps names→IDs; `teams.json` maps names/aliases→abbreviations |
| `server.py` | FastAPI app; `GET /` serves React build, `WS /audio` receives browser audio, `WS /ws` broadcasts stat JSON. **`_on_transcript()` is currently a stub** — the transcript→extract→stats→broadcast pipeline is not yet wired |
| `trigger_resolver.py` | *(planned)* One-time LLM call to resolve NHL API endpoint + fields |
| `trigger_store.py` | *(planned)* In-memory + JSON persistence for custom triggers |
| `trigger_runner.py` | *(planned)* Runtime keyword matching + HTTP fetch + field extraction |

### Frontend (`frontend/src/`)

| File | Role |
|---|---|
| `hooks/useMicCapture.ts` | `getUserMedia` + `MediaRecorder`; sends 3s audio blobs as binary over `WS /audio` |
| `hooks/useOverlaySocket.ts` | WS hook; auto-reconnect with exponential backoff; parses `Envelope { v:1, payload: StatPayload }` |
| `types/payloads.ts` | Full TS types: `PlayerPayload`, `GoaliePayload`, `TeamPayload`, `TriggerPayload`, `SystemPayload`, `StatPayload`, `Envelope` |
| `components/OverlayCanvas.tsx` | Card queue manager (max 3 visible, 2s dedup window, bottom-left stacked); `?debug` URL param shows countdown |
| `components/StatCard.tsx` | Skater stat card; slide-in, 8s auto-dismiss; goals=red, assists=blue |
| `components/GoalieCard.tsx` | Goalie stat card; teal accent |
| `components/TeamCard.tsx` | Team stat card; gold/amber accent |
| `TriggerCard.tsx` | *(planned)* Custom trigger card; purple/violet accent |
| `TriggerBuilder.tsx` | *(planned)* UI to create custom triggers with LLM-resolved endpoint preview |
| `TriggerList.tsx` | *(planned)* List/toggle/delete saved custom triggers |

**WebSocket message envelope:** all messages are `{ v: 1, payload: StatPayload }`. The `payload.type` discriminator selects the card component.

### Payload shapes (WebSocket messages)

All messages are wrapped in `{ v: 1, payload: StatPayload }`. The `payload.type` discriminator:
- `"player"` → `{ id, name, team, position, headshot_url, stats: { season, games_played, goals, assists, points, plus_minus }, display, ts }`
- `"goalie"` → `{ id, name, team, headshot_url, stats: { season, games_played, wins, losses, ot_losses, save_percentage, goals_against_avg, shutouts }, display, ts }`
- `"team"` → `{ name, abbrev, logo_url, stats: { season, wins, losses, ot_losses, points, games_played, goals_for, goals_against, point_pct }, conference_rank, division_rank, display, ts }`
- `"trigger"` → `{ id, keywords, description, fields: [{ label, value }], display, ts }`
- `"system"` → `{ event: 'connected'|'disconnected'|'transcriber_ready'|'transcriber_error', message, ts }`

## Key NHL API Endpoints

Base: `https://api-web.nhle.com/v1/`

- Player stats: `GET /player/{id}/landing`
- Team standings: `GET /standings/now` (all 32 teams in one response; cache as single entry)
- Player search: `GET https://search.d3.nhle.com/api/v1/search/player?q={name}&active=true`

`SEASON_ID` format: `<startYear><endYear>` e.g. `20232024`

## Data Files

- `backend/players.json` — `{ "Connor McDavid": 8478402, ... }` (~50 seeded players)
- `backend/teams.json` — `{ "Edmonton Oilers": "EDM", "Oilers": "EDM", ... }` (all 32 teams + common aliases)
- `backend/triggers.json` — *(planned)* persisted custom triggers

## Docker (planned)

- Default: only `backend` runs; FastAPI serves the pre-built React `dist/` at `GET /`
- `--profile full`: also starts a standalone nginx frontend on port 5173
- OBS Browser Source: `http://localhost:8000` at 1920×1080; enable "Allow audio capture" in OBS source settings
