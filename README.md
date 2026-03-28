# NHL Radio Overlay

A live broadcast overlay for OBS that listens to NHL radio commentary, transcribes it in real-time, extracts player and team names, fetches live stats from the NHL API, and displays animated stat cards in a browser source.

```
Browser mic → Deepgram → transcript → fuzzy extract → NHL API → WebSocket → animated OBS cards
```

## Demo

Cards appear automatically as you speak or listen to commentary. Say "McDavid scores" and a skater stat card slides in. Say "Oilers" and a team standings card appears. Cards stack (max 3), deduplicate within 2 seconds, and auto-dismiss after 8 seconds.

## Prerequisites

- Python 3.11+
- Node.js 20+
- [Deepgram API key](https://console.deepgram.com/) (free tier works)

## Setup

### Automated (Windows)

Run `setup.bat` once from the project root. It will:
- Create the Python virtual environment if missing
- Install all Python and Node dependencies
- Copy `.env.example` → `.env` if no `.env` exists
- Build the frontend `dist/` if it is empty

```bat
setup.bat
```

Then edit `.env` and set `DEEPGRAM_API_KEY` if prompted.

### Manual

**1. Environment:**

```bash
cp .env.example .env
# Edit .env and set DEEPGRAM_API_KEY
```

**2. Backend:**

```bash
cd backend
python -m venv .venv               # skip if .venv already exists

.venv/Scripts/python.exe -m pip install --quiet --upgrade pip setuptools wheel
.venv/Scripts/python.exe -m pip install --quiet --only-binary=:all: pydantic-core
.venv/Scripts/python.exe -m pip install --quiet -r requirements.txt"
```

**3. Frontend:**

```bash
cd frontend
npm install
npm run build   # outputs dist/ — required for the backend to serve the app
```

## Running

**Windows — both servers at once:**

```bat
dev.bat
```

**Manually:**

```bash
# Terminal 1 — backend (port 8000)
cd backend
.venv/Scripts/python.exe -m uvicorn server:app --reload --port 8000

# Terminal 2 — frontend dev server (port 5173)
cd frontend
npm run dev
```

Open `http://localhost:5173`, click **Start Mic**, and speak player or team names.

## OBS Setup

1. Add a **Browser Source** in OBS
2. URL: `http://localhost:8000` (serves the pre-built React app)
3. Width: `1920`, Height: `1080`
4. Check **"Allow audio capture"** in the source properties
5. In Display Capture / Game Capture settings, enable transparent background


## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `DEEPGRAM_API_KEY` | Yes | Real-time speech-to-text |
| `ANTHROPIC_API_KEY` | No | Claude (for LLM extractor mode) |
| `GEMINI_API_KEY` | No | Gemini (for LLM extractor mode) |
| `EXTRACTOR_MODE` | No | `"fuzzy"` (default) or `"llm"` |



### Manual injection (no mic required)

```bash
curl -X POST http://localhost:8000/debug/inject \
  -H "Content-Type: application/json" \
  -d '{"type": "player", "name": "Connor McDavid"}'
```

## Debug Mode

Append `?debug` to the URL to show an 8-second countdown on each card:

```
http://localhost:5173?debug
```

## Project Status

**Working:** end-to-end pipeline (audio capture → transcription → extraction → stats → overlay cards), all card types, WebSocket auto-reconnect, 45s stat cache, fuzzy entity extraction, full test suite.

**Planned:** Docker/`docker-compose.yml`, LLM extractor mode wiring, custom trigger system (`TriggerBuilder`, `TriggerCard`).

## NHL API

No authentication required.

| Endpoint | Purpose |
|---|---|
| `GET /v1/player/{id}/landing` | Player season stats (skater + goalie) |
| `GET /v1/standings/now` | All 32 teams + standings (single cached response) |
| `GET https://search.d3.nhle.com/api/v1/search/player?q={name}&active=true` | Player name → ID lookup |
