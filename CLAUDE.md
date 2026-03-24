# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**NHL Radio Overlay** — a live broadcast overlay that listens to NHL radio commentary, transcribes it in real-time, extracts player/team names, fetches live stats from the NHL API, and displays animated stat cards in a browser source for OBS.

## Running the App

```bash
# Copy and fill in API keys
cp .env.example .env

# Build and start (backend serves frontend)
docker compose up --build

# OBS Browser Source: http://localhost:8000 at 1920×1080
```

Required env vars (`.env`):
```
DEEPGRAM_API_KEY=
ANTHROPIC_API_KEY=
```

## Development (without Docker)

**Backend:**
```bash
cd backend
pip install -r requirements.txt
uvicorn server:app --reload --port 8000

# Run with mic input
python main.py --mode mic

# Run with audio file
python main.py --mode file --path sample.mp3
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev       # dev server at http://localhost:5173
npm run build     # outputs dist/ (required before docker build)
```

**Fuzzy extraction test:**
```bash
python testing_fuzz.py
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
| `main.py` | Entry point; wires transcriber → extractor → stats → broadcast |
| `transcriber.py` | Receives audio blobs from `WS /audio`, pipes to Deepgram; fires `on_transcript` for final segments only |
| `extractor.py` | Dual-mode: `"llm"` (Claude API) or `"fuzzy"` (RapidFuzz n-gram). Returns `{ players: [], teams: [] }` |
| `stats.py` | NHL API fetches with 45s in-memory cache. `players.json` maps names→IDs; `teams.json` maps names/aliases→abbreviations |
| `server.py` | FastAPI app; `GET /` serves React build, `WS /ws` broadcasts stat JSON |
| `trigger_resolver.py` | One-time LLM call at trigger-creation time to resolve NHL API endpoint + fields |
| `trigger_store.py` | In-memory + JSON persistence for custom triggers (`triggers.json`) |
| `trigger_runner.py` | Runtime keyword matching + HTTP fetch + field extraction for custom triggers |

### Frontend (`frontend/src/`)

| File | Role |
|---|---|
| `useMicCapture.ts` | `getUserMedia` + `MediaRecorder`; sends 3s audio blobs as binary over `WS /audio`; exposes `start()`, `stop()`, `isRecording`, `isConnected` |
| `useOverlaySocket.ts` | WS hook; auto-reconnect with exponential backoff; parses `PlayerPayload \| TeamPayload \| TriggerPayload` |
| `OverlayCanvas.tsx` | Card queue manager (max 3 visible, 2s dedup window, bottom-left stacked) |
| `StatCard.tsx` | Player stat card; slide-in, 8s auto-dismiss; goals=red, assists=blue |
| `TeamCard.tsx` | Team stat card; same animation; gold/amber accent |
| `TriggerCard.tsx` | Custom trigger card; purple/violet accent |
| `TriggerBuilder.tsx` | UI to create custom triggers with LLM-resolved endpoint preview |
| `TriggerList.tsx` | List/toggle/delete saved custom triggers |

### Payload shapes (WebSocket messages)

All messages carry a `type` discriminator:
- `"player"` → `{ player, stats: { goals, assists, points, plus_minus }, display }`
- `"team"` → `{ team, abbrev, stats: { wins, losses, ot_losses, points, goals_for, goals_against }, display }`
- `"trigger"` → `{ id, keywords, fields: [{ label, value }], display }`

### Custom Trigger system

Users create triggers via `POST /triggers` with `{ keywords, description }`. The backend calls Claude once to resolve the best-matching NHL API endpoint and fields. At runtime, keyword fuzzy-matching fires the stored HTTP call — no LLM involved. Triggers persist across restarts via `triggers.json`.

## Key NHL API Endpoints

Base: `https://api-web.nhle.com/v1/`

- Player stats: `GET /player/{id}/landing`
- Team standings: `GET /standings/now` (all 32 teams in one response; cache as single entry)
- Schedule: `GET /schedule/now`
- Boxscore: `GET /gamecenter/{GAME_ID}/boxscore`

`SEASON_ID` format: `<startYear><endYear>` e.g. `20232024`

## Data Files

- `backend/players.json` — `{ "Connor McDavid": 8478402, ... }` (~50 seeded players; extend via NHL API roster endpoint)
- `backend/teams.json` — `{ "Edmonton Oilers": "EDM", "Oilers": "EDM", ... }` (all 32 teams + common aliases)
- `backend/triggers.json` — persisted custom triggers (auto-created, do not edit manually)
- `backend/specs/api_spec_A.md` + `api_spec_B.md` — NHL API spec files used by the trigger resolver

## Docker

- Default: only `backend` runs; FastAPI serves the pre-built React `dist/` at `GET /`
- `--profile full`: also starts a standalone nginx frontend on port 5173
- No mic device passthrough needed — audio is captured in the browser via `getUserMedia`
- OBS browser source: enable "Allow audio capture" in OBS source settings for mic access
- Rebuild after frontend changes: `docker compose build && docker compose up`