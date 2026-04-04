# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**NHL Radio Overlay** — a live broadcast overlay that listens to NHL radio commentary, transcribes it in real-time, extracts player/team names, fetches live stats from the NHL API, and displays animated stat cards in a browser source for OBS.

## Current Implementation State

The core pipeline is fully wired end-to-end: audio → Deepgram → extractor → stats → broadcast.

**Implemented:**
- `backend/transcriber.py` — Deepgram WebSocket streaming transcriber
- `backend/extractor.py` — Fuzzy entity extraction (RapidFuzz n-gram); LLM mode partially wired
- `backend/stats.py` — `StatsClient` with 45s in-memory cache; `get_player()` (skater + goalie) and `get_team()` (standings) fully implemented
- `backend/server.py` — FastAPI app; `_on_transcript()` pipeline fully wired (transcript → extract → stats → broadcast); `POST /settings` syncs runtime config from frontend
- `frontend/src/App.tsx` — hash-router shell (wouter); wraps app in `SettingsProvider`; routes `/` → LandingPage, `/overlay` → OverlayPage, `/settings` → SettingsPage
- `frontend/src/contexts/SettingsContext.tsx` — 7 settings (model, language, fuzzy thresholds, cacheTtl, cardDisplayMs, maxCards); localStorage persistence; backend-bound keys auto-synced via `POST /settings`; frontend-only keys (cardDisplayMs, maxCards) not sent to backend
- `frontend/src/pages/` — `LandingPage` (recording toggle + WS status + nav), `OverlayPage` (memoized OverlayCanvas), `SettingsPage` (6 SettingsSlider controls)
- `frontend/src/components/` — `OverlayCanvas`, `StatCard`, `GoalieCard`, `TeamCard`, `MicHud`, `SettingsSlider` (all built with Tailwind + slide-in animations)
- `frontend/src/hooks/` — `useOverlaySocket.ts` (WS hook with auto-reconnect), `useMicCapture.ts` (getUserMedia + MediaRecorder)
- `frontend/src/types/payloads.ts` — full TypeScript payload types for all message shapes
- Tests: `backend/tests/` (pytest) and `frontend/src/components/__tests__/` + `frontend/src/hooks/__tests__/` (Vitest + Testing Library)

**Not yet built:** Docker / `docker-compose.yml`, `main.py`, trigger system (`trigger_resolver.py`, `trigger_store.py`, `trigger_runner.py`), `TriggerCard.tsx`, `TriggerBuilder.tsx`, `TriggerList.tsx`.

## Development

**Backend:**

The backend uses a virtual environment at `backend/.venv`. Always use it explicitly — never the system Python. All paths below are relative to the repo root.

```bash
backend/.venv/Scripts/python.exe -m pip install -r backend/requirements.txt
backend/.venv/Scripts/python.exe -m uvicorn server:app --reload --port 8000 --app-dir backend
```

Run tests:
```bash
backend/.venv/Scripts/python.exe -m pytest backend/tests/
backend/.venv/Scripts/python.exe -m pytest backend/tests/test_server.py -v   # single file
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
npx vitest run src/components/__tests__/StatCard.test.tsx   # single file
```

**Tests:**
```bash
# Backend
backend/.venv/Scripts/python.exe -m pytest tests/
backend/.venv/Scripts/python.exe -m pytest tests/test_stats.py -v

# Frontend (from frontend/)
npm run test
```

**When changing a function's output format** (payload shape, response structure, field names): grep for the function/endpoint across ALL test files — including `tests/test_*_live.py` which are excluded from pytest but still assert on real output. Run those scripts, and update any test that fails due to the format change. Do not assume pytest passing is sufficient coverage.

**Test gotcha — `frontend/dist` must exist before importing `server.py`:** The FastAPI `StaticFiles` mount raises at import time if the directory is missing. The test suite creates a minimal placeholder automatically (`conftest.py`), but if you add new test files that import `server` directly, ensure `frontend/dist/` exists first.

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

- If `DEEPGRAM_API_KEY` is missing the server still starts; `/debug/inject` and WS `/ws` work normally — useful for offline UI development.
- `EXTRACTOR_MODE=llm` is plumbed (env var + packages installed) but **not yet implemented** — only `"fuzzy"` runs regardless of this setting.

## Architecture

Audio is captured in the browser (no mic drivers or Docker device passthrough needed) and streamed to the backend over WebSocket.

```
Browser mic (getUserMedia + MediaRecorder)
→ WS /audio (binary blobs) → transcriber.py → Deepgram WebSocket → transcript
→ extractor.py (LLM or fuzzy) → { players, teams }
→ stats.py (NHL API + 45s cache) → PlayerPayload / TeamPayload
→ FastAPI WS /ws → React OverlayCanvas → StatCard / TeamCard
```

### Configuration

**Any tunable constant (timeout, threshold, URL, limit, interval, model name) MUST live in a config file — never hardcoded inline in a module.** This is a strict rule for this project.

- **Backend:** `backend/config.py` — NHL API URLs, HTTP timeout, cache TTL, fuzzy matching thresholds, Deepgram model/language/reconnect settings. All plain Python constants grouped by domain. Secrets (API keys) stay in `.env`.
- **Frontend:** `frontend/src/config.ts` — WebSocket URLs, card display timer, max visible cards, dedup window, mic timeslice, reconnect backoff. Exported TS constants. `MAX_CARDS` and `CARD_DISPLAY_MS` are compile-time defaults only — runtime values come from `SettingsContext` (which reads localStorage). Tailwind visual classes (colors, sizes) stay inline in components.

When adding a new feature or module, if it introduces any value that could reasonably be tuned in production (e.g. a polling interval, a retry count, a batch size, an API endpoint), add it to the appropriate config file with a descriptive comment — do not define it locally in the module.

### Backend (`backend/`)

| File | Role |
|---|---|
| `main.py` | *(planned)* Entry point; wires transcriber → extractor → stats → broadcast |
| `transcriber.py` | Receives audio blobs from `WS /audio`, pipes to Deepgram; fires `on_transcript` for final segments only |
| `extractor.py` | Dual-mode: `"llm"` (Claude/Gemini) or `"fuzzy"` (RapidFuzz n-gram). Returns `{ players: [], teams: [] }` |
| `stats.py` | NHL API fetches with 45s in-memory cache. `players.json` maps names→IDs; `teams.json` maps names/aliases→abbreviations |
| `server.py` | FastAPI app; `GET /` serves React build, `WS /audio` receives browser audio, `WS /ws` broadcasts stat JSON, `POST /debug/inject` manually injects a stat payload for testing, `POST /settings` updates runtime config (model, language, fuzzy thresholds, cacheTtl) |
| `trigger_resolver.py` | *(planned)* One-time LLM call to resolve NHL API endpoint + fields |
| `trigger_store.py` | *(planned)* In-memory + JSON persistence for custom triggers |
| `trigger_runner.py` | *(planned)* Runtime keyword matching + HTTP fetch + field extraction |

### Frontend (`frontend/src/`)

| File | Role |
|---|---|
| `contexts/SettingsContext.tsx` | 7 settings (model, language, fuzzyNgramThreshold, fuzzyPartialThreshold, cacheTtl, cardDisplayMs, maxCards); localStorage-persisted; backend-bound keys auto-POST to `/settings` on change |
| `pages/LandingPage.tsx` | Control panel: recording start/stop toggle, WS connection indicator, nav links to `/overlay` and `/settings` |
| `pages/OverlayPage.tsx` | Memoized `OverlayCanvas` wrapper; use `/#/overlay` as the OBS browser source URL |
| `pages/SettingsPage.tsx` | Six `SettingsSlider` controls covering all 7 settings |
| `hooks/useMicCapture.ts` | `getUserMedia` + `MediaRecorder`; sends 250ms audio blobs as binary over `WS /audio` |
| `hooks/useOverlaySocket.ts` | WS hook; auto-reconnect with exponential backoff; parses `Envelope { v:1, payload: StatPayload }` |
| `types/payloads.ts` | Full TS types: `PlayerPayload`, `GoaliePayload`, `TeamPayload`, `TriggerPayload`, `SystemPayload`, `StatPayload`, `Envelope` |
| `components/OverlayCanvas.tsx` | Card queue manager (max cards + display time from SettingsContext, 2s dedup window, bottom-left stacked); `?debug` URL param shows countdown |
| `components/StatCard.tsx` | Skater stat card; slide-in, auto-dismiss; goals=red, assists=blue |
| `components/GoalieCard.tsx` | Goalie stat card; teal accent |
| `components/TeamCard.tsx` | Team stat card; gold/amber accent |
| `components/SettingsSlider.tsx` | Discrete-stop range slider with label, description, and stop array |
| `components/MicHud.tsx` | *(unused in routing)* Recording control HUD; mic capture is now handled in LandingPage |
| `utils/initials.ts` | Derives 2-letter initials from a full name (used in card avatars) |
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

Both JSON files are loaded once at startup; changes require a server restart.

**To add a new player:** add `"First Last": NHL_PLAYER_ID` to `players.json` — no code changes needed. The extractor will match both full-name and surname-only mentions automatically.

## Development Workflows

**Local dev (two processes):**
```bash
# Terminal 1 — backend
cd backend && ../.venv/Scripts/python.exe -m uvicorn server:app --reload --port 8000

# Terminal 2 — frontend hot-reload
cd frontend && npm run dev   # http://localhost:5173
```
`npm run build` is only needed when serving the frontend through the backend at port 8000.

Or use the convenience script at the repo root:
```bat
dev.bat            # starts both backend and frontend in separate windows
dev.bat backend    # backend only
dev.bat build      # builds frontend, then starts backend only
```

**Injecting a stat payload without a microphone:**
```bash
# Player by name
curl -X POST http://localhost:8000/debug/inject \
  -H "Content-Type: application/json" \
  -d '{"type": "player", "name": "Connor McDavid"}'

# Team by abbreviation
curl -X POST http://localhost:8000/debug/inject \
  -H "Content-Type: application/json" \
  -d '{"type": "team", "abbrev": "EDM"}'
```

**Adding a new card type:**
1. Add a new payload type to `frontend/src/types/payloads.ts`
2. Create the card component in `frontend/src/components/`
3. Register it in `OverlayCanvas.tsx` — the `CardWrapper` render block is where `payload.type` is switched on
4. Add the corresponding payload builder in `backend/stats.py` and wire it in `_handle_transcript()` in `server.py`
5. Keep payload shape in sync between `types/payloads.ts` and the Python TypedDict in `stats.py`

**Debugging overlay cards:** append `?debug` to the OBS browser source URL to show an 8-second countdown badge on each visible card. Useful for verifying dedup and timer-reset behaviour.

## Docs Folder

Whenever you create a new file in `docs/`, add an entry for it in `docs/README.md` under the appropriate subfolder section — one line is enough.

## Docker (planned)

- Default: only `backend` runs; FastAPI serves the pre-built React `dist/` at `GET /`
- `--profile full`: also starts a standalone nginx frontend on port 5173
- OBS Browser Source: `http://localhost:8000/#/overlay` at 1920×1080 (the `/` route is the control panel, not the overlay); enable "Allow audio capture" in OBS source settings
