# NHL Radio Overlay — Task List

Derived from `plan.md`. Each task is atomic, completable in under 2 hours, and ordered by dependency.

---

## Day 1 — Backend Pipeline

### SETUP

- [X] **SETUP-01** — Create repo structure: `backend/`, `frontend/`, `.env`, `.env.example`, `README.md`
- [X] **SETUP-02** — Create `backend/requirements.txt` with: `fastapi[standard]`, `uvicorn`, `websockets`, `deepgram-sdk`, `anthropic`, `httpx`, `python-dotenv`, `rapidfuzz` , `google-genai`
- [X] **SETUP-03** — Run `pip install -r requirements.txt`, verify all imports resolve
- [X] **SETUP-04** — Create `.env.example` with `DEEPGRAM_API_KEY=` and `ANTHROPIC_API_KEY=` placeholders; create `.env` with real keys; add `.env` to `.gitignore`
- [X] **SETUP-05** — Scaffold `frontend/` with Vite + React + TypeScript: `npm create vite@latest frontend -- --template react-ts`
- [X] **SETUP-06** — Add Tailwind CSS to the Vite project (`tailwindcss`, `postcss`, `autoprefixer`)

---

### MIC CAPTURE — `frontend/src/useMicCapture.ts`

- [ ] **MIC-01** — Implement `useMicCapture(audioWsUrl: string)` hook:
  - Call `navigator.mediaDevices.getUserMedia({ audio: true })` on start
  - Open a WebSocket to `ws://localhost:8000/audio`
  - Use `MediaRecorder` with a 3s `timeslice` to emit audio blobs
  - Send each blob as binary over the WebSocket on `ondataavailable`
  - Expose `{ start(), stop(), isRecording: boolean, isConnected: boolean }`
- [ ] **MIC-02** — Add a mic control button to the overlay UI (start/stop recording, connection status indicator)
- [ ] **MIC-03** — Test in OBS browser source: confirm mic access is granted and blobs are received by the backend

---

### TRANSCRIPTION — `backend/transcriber.py`

- [X] **TRANS-01** — Implement `DeepgramTranscriber` class that accepts a Deepgram API key and an `on_transcript(text: str, is_final: bool)` callback
- [X] **TRANS-02** — Connect Deepgram WebSocket using the SDK's `listen.live` interface with `model="nova-2"`, `language="en"`, `punctuate=True`. refer to the deepgram skill
- [X] **TRANS-03** — Implement `send_audio(blob: bytes)` method that pipes raw audio blobs from the browser directly to the open Deepgram WebSocket
- [X] **TRANS-04** — Confirm final transcripts print to terminal within 1 second of speech arriving at the backend

---

### EXTRACTION — `backend/extractor.py`

- [ ] **EXTR-01** — Define the return type: `ExtractionResult = TypedDict("ExtractionResult", { "players": list[str], "teams": list[str] })`; implement `extract_entities(text: str, mode: str = "llm") -> ExtractionResult` with mode toggle
- [ ] **EXTR-02** — **"llm" mode — prompt**
  - Write system prompt instructing Claude to return only a JSON object `{ "players": [...], "teams": [...] }` with full canonical names; never infer; return empty lists if none found
  - Include few-shot examples: one with a player mention, one with a team mention, one with both, one with neither
- [ ] **EXTR-03** — **"llm" mode — API call**
  - Call `anthropic.Anthropic().messages.create()` with the system prompt and transcript as user message
  - Strip markdown fences if present, `json.loads()` the response, validate keys `"players"` and `"teams"` exist
  - Catch all exceptions; return `{ "players": [], "teams": [] }` on any failure
- [X] **EXTR-04** — **"fuzzy" mode — player matching** 
  - Generate n-grams (1–3 words) from the transcript
  - Match each n-gram against keys in `players.json` using RapidFuzz (`scorer=fuzz.token_sort_ratio`, threshold >= 85)
  - Return matched canonical full player names, deduplicated
- [X] **EXTR-05** — **"fuzzy" mode — team matching** 
  - Load `teams.json` (including short aliases: `"Oilers"`, `"Leafs"`, `"Habs"`, etc.)
  - Apply same n-gram + RapidFuzz approach (threshold >= 85) against all keys
  - Resolve matched alias to canonical team name (e.g., `"Oilers"` -> `"Edmonton Oilers"`)
  - Return matched canonical team names, deduplicated
- [ ] **EXTR-06** — **Consistency check**: ensure both modes return the same shape `{ "players": List[str], "teams": List[str] }` with full canonical names; add a `normalize()` helper if needed
- [X] **EXTR-07** — **Unit tests** with 6 sample transcripts:
  - 2 with clear player name(s) only
  - 2 with clear team name(s) only (including a short alias like "the Leafs")
  - 1 with both player and team mentioned
  - 1 empty / irrelevant string
  - Verify correct outputs for both `"llm"` and `"fuzzy"` modes

---

### STATS — `backend/stats.py`

Reference: https://gitlab.com/dword4/nhlapi/-/blob/master/new-api.md

- [X] **STATS-01** — **`players.json`**: seed with 50 top NHL players as `{ "Full Name": player_id }` using the NHL API player search or a known list 
- [X] **STATS-02** — **`teams.json`**: create mapping for all 32 NHL teams including common short aliases: 
  ```json
  {
    "Edmonton Oilers": "EDM",
    "Oilers": "EDM",
    "Toronto Maple Leafs": "TOR",
    "Leafs": "TOR",
    "Montreal Canadiens": "MTL",
    "Habs": "MTL"
  }
  ```
- [X] **STATS-03** — Implement `lookup_player_id(name: str) -> int | None` with case-insensitive match against `players.json` 
- [X] **STATS-04** — Implement `lookup_team_abbrev(name: str) -> str | None` with case-insensitive match against `teams.json`; resolves aliases to abbreviation 
- [x] **STATS-05** — Implement `StatsClient.get_player(player_id: int, name: str) -> dict | None`:
  - Call `GET https://api-web.nhle.com/v1/player/{id}/landing`
  - Returns an extracted intermediate dict (not raw API, not a broadcast payload) — see architecture note below
  - Sets `_type: "skater" | "goalie"` based on `positionCode == "G"` detection
  - Extracts: `id`, `name` (firstName + lastName), `team` (currentTeamAbbrev), `position` (positionCode), `headshot_url` (headshot)
  - `stats.season` (str), `stats.games_played`
  - Skater stats: `goals`, `assists`, `points`, `plus_minus` (plusMinus)
  - Goalie stats: `wins`, `losses`, `ot_losses` (otLosses), `save_percentage` (savePctg), `goals_against_avg` (goalsAgainstAvg), `shutouts`
  - Returns `None` on any HTTP or parse error 
- [x] **STATS-06** — Implement `StatsClient.get_team(abbrev: str) -> dict | None`:
  - Call `GET https://api-web.nhle.com/v1/standings/now`; cache entire response as key `"standings"`
  - Filter by `teamAbbrev` (case-insensitive); returns `None` if not found
  - Extracts: `name` (teamName.default), `abbrev`, `logo_url` (constructed: `.../svg/{abbrev}_light.svg`)
  - `stats.season` (top-level season as str), `wins`, `losses`, `ot_losses` (otLosses), `points`, `games_played` (gamesPlayed)
  - `goals_for` (goalFor), `goals_against` (goalAgainst), `point_pct` (pointPctg)
  - `conference_rank` (conferenceSequence), `division_rank` (divisionSequence)
  - Returns `None` on any HTTP or parse error
- [x] **STATS-07** — 45-second in-memory cache on `StatsClient._cache: dict[str, tuple[float, dict]]`:
  - Cache key: `f"player:{player_id}"` for players, `"standings"` for all 32 teams (single fetch)
  - Uses `time.monotonic()` for TTL check
  - **Architecture decision:** fetch methods return extracted intermediate dicts (not raw API). Reasoning: goalie detection belongs in fetch (positionCode is available there); cache stores compact extracted data; `build_*_payload()` stays a pure formatting function, easy to unit test.
- [x] **STATS-08** — `build_player_payload(extracted: dict) -> PlayerPayload`:
  - Input: extracted dict from `get_player()` with `_type == "skater"`
  - Adds `display` (e.g. `"McDavid · 32G  100A  132PTS  +15"`, plus_minus with sign) and `ts` (Unix ms)
  - Returns full contract shape: `{ type, id, name, team, position, headshot_url, stats, display, ts }`
- [x] **STATS-09** — `build_team_payload(extracted: dict) -> TeamPayload`:
  - Input: extracted dict from `get_team()`
  - Adds `display` (e.g. `"EDM · 42W  20L  5OT  89PTS"`) and `ts`
  - Returns full contract shape: `{ type, name, abbrev, logo_url, stats, conference_rank, division_rank, display, ts }`
- [x] **STATS-10** — Tests in `backend/tests/test_stats.py` (19 tests, all passing, no network):
  - `get_player`: skater fields, goalie fields, HTTP error → None, cache hit (single HTTP call)
  - `get_team`: all fields, case-insensitive abbrev, team not found → None, HTTP error → None, cache hit
  - `build_player_payload`: type, display format, negative plus_minus, ts
  - `build_goalie_payload`: type, display format, ts
  - `build_team_payload`: type, display format, ts
- [x] **STATS-11** — `build_goalie_payload(extracted: dict) -> GoaliePayload` (STATS-12 merged here):
  - Input: extracted dict from `get_player()` with `_type == "goalie"`
  - `display` format: `"Markstrom · .907 SV%  2.98 GAA  2 SO"` (save_percentage without leading zero)
  - Returns full contract shape: `{ type, id, name, team, headshot_url, stats, display, ts }`

---

### SERVER — `backend/server.py`

- [X] **SERV-01** — Create FastAPI app with `GET /` that serves `frontend/dist/index.html` (use `StaticFiles`) 
- [X] **SERV-02** — Implement `WS /audio` endpoint: accept browser audio blobs, forward each blob to `DeepgramTranscriber.send_audio()` 
- [X] **SERV-03** — Implement `WS /ws` endpoint: accept connections, store in a `set`, broadcast stat JSON to all active clients 
- [X] **SERV-04** — Implement `broadcast(payload: dict)` helper: wrap in versioned envelope `{ "v": 1, "payload": payload }`, `json.dumps` and send to all `/ws` clients, remove disconnected clients silently 
- [X] **SERV-05** — Wire full async pipeline: on `is_final` transcript from Deepgram →
  - `extract_entities()` →
  - For each player name → `lookup_player_id()` → `client.get_player()` → check `_type` → `build_player_payload()` or `build_goalie_payload()` → `broadcast()`
  - For each team name → `lookup_team_abbrev()` → `client.get_team()` → `build_team_payload()` → `broadcast()`
- [ ] **SERV-06** — Test end-to-end: run server, send a test audio blob to `WS /audio`, verify transcript arrives and stat payloads broadcast on `WS /ws`
- [ ] **SERV-07** — Emit `SystemPayload` events over `WS /ws`:
  - New `/ws` client connects: `{ type: "system", event: "connected", message: "Overlay connected", ts }`
  - `/ws` client disconnects: `{ type: "system", event: "disconnected", message: "Overlay disconnected", ts }`
  - Deepgram WebSocket opens: `{ type: "system", event: "transcriber_ready", message: "Deepgram connected", ts }`
  - Deepgram error / bad key: `{ type: "system", event: "transcriber_error", message: <error detail>, ts }`

---

## Day 2 — React Frontend + Integration

### WEBSOCKET HOOK — `frontend/src/useOverlaySocket.ts`

- [ ] **WS-01** — Copy the full TypeScript block from `docs/api/ws-payload-contract.md` into `frontend/src/types/payloads.ts` and export all types:
  `PlayerPayload`, `GoaliePayload`, `TeamPayload`, `TriggerPayload`, `SystemPayload`, `StatPayload`, `Envelope`
  All messages are wrapped in `{ v: 1, payload: StatPayload }` — the hook must unwrap the envelope.
- [ ] **WS-02** — Implement `useOverlaySocket(url: string)` custom hook; connect to WS on mount, auto-reconnect on close (exponential backoff, max 5s delay)
- [ ] **WS-03** — Parse incoming messages: unwrap envelope (`msg.payload`) before discriminating on `type`; handle `"player"`, `"goalie"`, `"team"`, `"trigger"`, `"system"` types
- [ ] **WS-04** — Return `{ latestPayload: StatPayload | null, systemEvent: SystemPayload | null, isConnected: boolean }` from the hook

---

### STAT CARD — `frontend/src/StatCard.tsx`

- [ ] **CARD-01** — Create `StatCard` component accepting props: `payload: PlayerPayload`, `onExpire: () => void`
- [ ] **CARD-02** — Style card: dark semi-transparent background (`bg-black/80`), white bold player name, colored stat values (goals red, assists blue, points white, plus/minus green/red conditional)
- [ ] **CARD-03** — Add entrance animation: slide in from left + fade in using Tailwind `animate-` or a CSS keyframe (`@keyframes slideIn`)
- [ ] **CARD-04** — Add exit animation: fade out on expire
- [ ] **CARD-05** — Implement auto-expire: `useEffect` sets `setTimeout(onExpire, 8000)` on mount, clears on unmount

---

### TEAM CARD — `frontend/src/TeamCard.tsx`

- [ ] **TEAM-01** — Create `TeamCard` component accepting props: `payload: TeamPayload`, `onExpire: () => void`
- [ ] **TEAM-02** — Style card: same dark semi-transparent background as `StatCard`; team abbreviation large and bold in gold/amber (`text-amber-400`); W–L–OT record and points total prominent in white
- [ ] **TEAM-03** — Reuse the same entrance/exit animation keyframes as `StatCard` (extract to a shared `animations.css` or Tailwind plugin if needed)
- [ ] **TEAM-04** — Implement auto-expire with same `useEffect` / `setTimeout(onExpire, 8000)` pattern as `StatCard`

---

### GOALIE CARD — `frontend/src/GoalieCard.tsx`

- [ ] **GOALIE-01** — Create `GoalieCard` component accepting `payload: GoaliePayload`, `onExpire: () => void`
- [ ] **GOALIE-02** — Style card: same dark semi-transparent background as `StatCard`; teal/cyan accent (`text-cyan-400`) to distinguish from skater cards; show name, team, headshot; stats: SV%, GAA, shutouts, W–L–OT
- [ ] **GOALIE-03** — Reuse entrance/exit animation and `useEffect` / `setTimeout(onExpire, 8000)` auto-expire pattern from `StatCard`

---

### OVERLAY CANVAS — `frontend/src/OverlayCanvas.tsx`

- [ ] **OVL-01** — Implement `OverlayCanvas` component: holds `cards: Array<StatPayload & { id: string }>` in state (add a unique `id = player/team + timestamp` on arrival)
- [ ] **OVL-02** — Use `useOverlaySocket` hook; push `latestPayload` to card queue when it changes (deduplicate same entity within 2s window to avoid flicker)
- [ ] **OVL-03** — Limit visible cards to 3: drop oldest if queue exceeds 3
- [ ] **OVL-04** — Render cards stacked bottom-left: `absolute bottom-8 left-8 flex flex-col-reverse gap-3`; route by `payload.type`: `"player"` → `<StatCard>`, `"goalie"` → `<GoalieCard>`, `"team"` → `<TeamCard>`, `"system"` → update status indicator (do NOT add to card queue)
- [ ] **OVL-05** — Handle `onExpire` callback: remove card from state by its `id`

---

### ROOT — `frontend/src/main.tsx`

- [ ] **ROOT-01** — Set root `div` to `w-screen h-screen bg-transparent overflow-hidden relative`
- [ ] **ROOT-02** — Mount `<OverlayCanvas />` as the only child
- [ ] **ROOT-03** — Set `index.html` body background to `transparent`, add `<meta>` for OBS browser source compatibility

---

### DOCKER

- [ ] **DOCK-01** — Write `backend/Dockerfile`:
  - Base: `python:3.11-slim`
  - No system audio deps needed (mic runs in browser)
  - `COPY requirements.txt .` -> `pip install --no-cache-dir -r requirements.txt`
  - `COPY . .`
  - `EXPOSE 8000`
  - `CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]`
- [ ] **DOCK-02** — Write `frontend/Dockerfile` as a multi-stage build:
  - Stage 1 `builder`: `node:20-alpine`, `npm ci`, `npm run build` -> outputs `dist/`
  - Stage 2 `server`: `nginx:alpine`, copy `dist/` into `/usr/share/nginx/html`, `EXPOSE 80`
- [ ] **DOCK-03** — Write `docker-compose.yml`:
  - `backend` service: `build: ./backend`, `ports: ["8000:8000"]`, `env_file: .env`
  - No mic device passthrough needed
  - `frontend` service (opt-in): `build: ./frontend`, `ports: ["5173:80"]`, `profiles: ["full"]`
- [ ] **DOCK-04** — Ensure the backend image includes the built frontend: add a `COPY --from=frontend-builder /app/dist ./frontend/dist` stage in `backend/Dockerfile` (or document a `make build` step that builds frontend first and copies `dist/` before `docker compose up`)
- [ ] **DOCK-05** — Add `.dockerignore` for both services:
  - `backend/.dockerignore`: `__pycache__/`, `*.pyc`, `.env`, `*.egg-info`
  - `frontend/.dockerignore`: `node_modules/`, `dist/`, `.env`
- [ ] **DOCK-06** — Smoke test the full Docker setup:
  - `docker compose build` completes without errors
  - `docker compose up` starts backend healthy on port 8000
  - `curl http://localhost:8000/` returns the React HTML (not a 404)
  - WebSocket connection to `ws://localhost:8000/ws` accepts and stays open

---

### INTEGRATION & POLISH

- [ ] **INT-01** — Build frontend: `npm run build` inside `frontend/`, verify `dist/` is generated
- [ ] **INT-02** — Confirm `GET /` on FastAPI serves the React build correctly (no 404 on reload)
- [ ] **INT-03** — Full pipeline test with a 30-second real NHL broadcast audio clip: verify at least 1 player card and 1 team card appear correctly
- [ ] **INT-04** — Test OBS integration: add browser source at `http://localhost:8000`, set 1920×1080, confirm transparent background and correct card positioning
- [ ] **INT-05** — Tune card timing: verify 8s dismiss feels correct on screen, adjust if needed
- [ ] **INT-06** — Write `README.md` covering:
  - Prerequisites: Docker Desktop (or Docker + Docker Compose plugin)
  - Setup: `cp .env.example .env` -> fill in API keys -> `docker compose up --build`
  - OBS browser source config: URL `http://localhost:8000`, resolution 1920×1080, transparent background checked
  - Live mic mode vs file mode (how to pass CLI args via `docker compose run`)
  - How to add players to `players.json` and team aliases to `teams.json`
  - How to rebuild after frontend changes (`docker compose build && docker compose up`)

---

## Optional Enhancements (post-MVP)

- [ ] **OPT-01** — Expand `players.json` to full NHL roster via a one-time script hitting the NHL API roster endpoint
- [ ] **OPT-02** — Add a `ConnectionStatus` indicator in the overlay (green dot = connected, red = reconnecting)
- [ ] **OPT-03** — Add duplicate suppression: if same player or team card was shown in last 30s, skip re-display
- [ ] **OPT-04** — Add team logo images to `TeamCard` (NHL CDN URLs, no auth required)
- [ ] **OPT-05** — Publish image to Docker Hub so users can `docker pull` instead of building locally

---

## Task Summary

| Area | Tasks | Day |
|---|---|---|
| Setup | SETUP-01 → 06 | Day 1 AM |
| Mic Capture (frontend) | MIC-01 → 03 | Day 1 AM |
| Transcription | TRANS-01 → 04 | Day 1 AM |
| Extraction | EXTR-01 → 07 | Day 1 PM |
| Stats | STATS-01 → 11 | Day 1 PM |
| Server | SERV-01 → 05 | Day 1 PM/Eve |
| WS Hook | WS-01 → 04 | Day 2 AM |
| StatCard | CARD-01 → 05 | Day 2 AM |
| TeamCard | TEAM-01 → 04 | Day 2 AM |
| OverlayCanvas | OVL-01 → 05 | Day 2 AM |
| Root + Build | ROOT-01 → 03 | Day 2 PM |
| Docker | DOCK-01 → 06 | Day 2 PM |
| Integration | INT-01 → 06 | Day 2 PM/Eve |
