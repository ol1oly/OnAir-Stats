# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**NHL Radio Overlay** — a live broadcast overlay that listens to NHL radio commentary, transcribes it in real-time, extracts player/team names, fetches live stats from the NHL API, and displays animated stat cards in a browser source for OBS.

## Current Implementation State

The project is in active development. The backend core is functional; the frontend and Docker setup are not yet built.

**Implemented:**
- `backend/transcriber.py` — Deepgram WebSocket streaming transcriber
- `backend/extractor.py` — Fuzzy entity extraction (RapidFuzz n-gram); LLM mode planned but not wired
- `backend/stats.py` — `StatsClient` lookups work; `get_player()` and `get_team()` raise `NotImplementedError` (pending)
- `backend/server.py` — FastAPI with `WS /audio`, `WS /ws`, and static file serving
- `backend/players.json` / `backend/teams.json` — entity data files
- Frontend: default Vite + React scaffold (no overlay components yet)

**Not yet built:** Docker / `docker-compose.yml`, `main.py`, trigger system (`trigger_resolver.py`, `trigger_store.py`, `trigger_runner.py`), all frontend overlay components.

## Development

**Backend:**
```bash
cd backend
pip install -r requirements.txt
uvicorn server:app --reload --port 8000
```
### Python Dependencies
When installing any Python package:
- Use `pip install <package>`
- Add the package and its version to requirements.txt manually (e.g. `requests==2.31.0`)
- Do not use `pip freeze` as it captures indirect dependencies — only add the package you explicitly installed

**Frontend:**
```bash
cd frontend
npm install
npm run dev       # dev server at http://localhost:5173
npm run build     # outputs dist/ (required before serving from backend)
npm run lint
```

**Standalone module tests (no server needed):**
```bash
# Test extractor against sample sentences
python backend/extractor.py "McDavid scores against the Maple Leafs"

# Test transcriber against an audio file or mic
python backend/transcriber.py sample.mp3
python backend/transcriber.py --mic
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
| `server.py` | FastAPI app; `GET /` serves React build, `WS /ws` broadcasts stat JSON |
| `trigger_resolver.py` | *(planned)* One-time LLM call to resolve NHL API endpoint + fields |
| `trigger_store.py` | *(planned)* In-memory + JSON persistence for custom triggers |
| `trigger_runner.py` | *(planned)* Runtime keyword matching + HTTP fetch + field extraction |

### Frontend (`frontend/src/`) — planned components

| File | Role |
|---|---|
| `useMicCapture.ts` | `getUserMedia` + `MediaRecorder`; sends 3s audio blobs as binary over `WS /audio` |
| `useOverlaySocket.ts` | WS hook; auto-reconnect with exponential backoff; parses `PlayerPayload \| TeamPayload \| TriggerPayload` |
| `OverlayCanvas.tsx` | Card queue manager (max 3 visible, 2s dedup window, bottom-left stacked) |
| `StatCard.tsx` | Player stat card; slide-in, 8s auto-dismiss; goals=red, assists=blue |
| `TeamCard.tsx` | Team stat card; gold/amber accent |
| `TriggerCard.tsx` | Custom trigger card; purple/violet accent |
| `TriggerBuilder.tsx` | UI to create custom triggers with LLM-resolved endpoint preview |
| `TriggerList.tsx` | List/toggle/delete saved custom triggers |

### Payload shapes (WebSocket messages)

All messages carry a `type` discriminator:
- `"player"` → `{ player, stats: { goals, assists, points, plus_minus }, display }`
- `"team"` → `{ team, abbrev, stats: { wins, losses, ot_losses, points, goals_for, goals_against }, display }`
- `"trigger"` → `{ id, keywords, fields: [{ label, value }], display }`

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
