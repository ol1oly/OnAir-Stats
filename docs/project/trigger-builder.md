# NHL Overlay — Custom Trigger Builder: Plan & Tasks

> Full specification for the custom trigger system: data model, resolver flow, API routes, and post-MVP advanced capabilities (input slots, chained endpoints, trigger composition).

## Feature Overview

End users can create **custom triggers** from the frontend. A trigger binds one or more **keywords** to a **natural language description** of data they want displayed. When those keywords are detected in the live audio (via fuzzy or LLM matching), the backend calls the pre-resolved NHL API endpoint and pushes the relevant fields to the overlay as a card.

The LLM is only involved **at trigger-creation time** — it reads the two NHL API spec files once, determines which endpoint best matches the description, and identifies which response fields to extract. At runtime, the backend simply calls that stored endpoint and maps the stored fields. No LLM call happens during live audio for custom triggers.

---

## End-to-End User Flow

```
[Frontend — Trigger Builder UI]
  User fills in:
    · Keywords:    "power play"
    · Description: "Show how many power play goals the Oilers have scored this season"
          │
          ▼ POST /triggers
[Backend — trigger_resolver.py]
  1. Load api_spec_A.md + api_spec_B.md
  2. Pre-filter sections by keyword overlap (ranker)
  3. Send top candidates + description to Claude
  4. Claude returns:
       {
         "endpoint": "https://api-web.nhle.com/v1/club-stats/EDM/now",
         "method": "GET",
         "path_params": { "team": "EDM" },    ← dynamic params noted
         "fields": [
           { "path": "skaters[].powerPlayGoals", "label": "PP Goals",  "type": "number" },
           { "path": "skaters[].firstName",      "label": "First Name", "type": "string" },
           { "path": "skaters[].lastName",       "label": "Last Name",  "type": "string" }
         ],
         "notes": "Filter skaters[] by playerId or sort by powerPlayGoals desc for leaders."
       }
  5. Trigger saved to triggers store:
       {
         "id": "uuid",
         "keywords": ["power play"],
         "description": "Show how many power play goals...",
         "endpoint": "https://api-web.nhle.com/v1/club-stats/EDM/now",
         "method": "GET",
         "fields": [...],
         "notes": "...",
         "enabled": true
       }
          │
          ▼
[Runtime — live audio pipeline]
  Transcript arrives → fuzzy/LLM entity extraction runs →
  "power play" matched against active trigger keywords →
  Backend calls stored endpoint →
  Extracts stored fields from response →
  Builds display payload →
  Broadcasts to overlay → TriggerCard rendered for 8s
```

---

## Architecture

```
radio-nhl-overlay/
└── backend/
    ├── trigger_resolver.py   — LLM-based endpoint + field resolution (creation time only)
    ├── trigger_store.py      — in-memory store + JSON persistence for triggers
    ├── trigger_runner.py     — runtime: keyword match → HTTP call → field extraction → payload
    └── specs/
        ├── api_spec_A.md     — NHL API spec file A
        └── api_spec_B.md     — NHL API spec file B

└── frontend/
    └── src/
        ├── TriggerBuilder.tsx  — form to create a new trigger
        ├── TriggerList.tsx     — list, toggle, delete existing triggers
        ├── TriggerCard.tsx     — overlay card for custom trigger results
        └── useTriggers.ts      — REST hook for CRUD operations on /triggers
```

New FastAPI routes added to `server.py`:
```
POST   /triggers          — create trigger (calls resolver, saves result)
GET    /triggers          — list all triggers
PATCH  /triggers/{id}     — enable / disable a trigger
DELETE /triggers/{id}     — delete a trigger
```

---

## Backend Modules

### `trigger_resolver.py`
Called once when the user creates a trigger. Never called during live audio.

- Loads and sections both spec files
- Pre-filters sections by keyword overlap (same ranker logic as extractor)
- Sends top-N candidate sections + user description to Claude with a strict system prompt
- Claude returns a `TriggerResolution` JSON object (endpoint, method, fields, notes)
- Validates the response shape; raises if endpoint or fields are missing
- Returns the resolution to be stored alongside the trigger definition

**System prompt for resolver:**
```
You are an NHL API expert. You will receive:
  1. A natural language description of data an end user wants to display on a live broadcast overlay
  2. Candidate sections from two NHL API specification files

Your task:
  - Identify the single best-matching endpoint
  - List only the response fields that directly satisfy the description
    Each field must include: JSON path (dot notation), a short display label, and value type
  - If the endpoint requires dynamic path parameters (e.g. team abbreviation, player ID),
    note them in "path_params" so the backend knows what to substitute at runtime
  - If no section is a confident match, return { "endpoint": null, "error": "..." }
  - Respond ONLY with valid JSON. No markdown fences. No explanation outside the JSON.
```

### `trigger_store.py`
- In-memory dict `{ id: TriggerRecord }` loaded from / persisted to `triggers.json` on disk
- `TriggerRecord` shape:
  ```python
  {
    "id":          str,         # uuid4
    "keywords":    list[str],   # ["power play"] — 1–3 words
    "description": str,         # user's free-text intent
    "endpoint":    str,         # resolved URL (may contain {param} placeholders)
    "method":      str,         # "GET" (all NHL API endpoints are GET)
    "path_params": dict,        # { "team": "EDM" } — filled at creation; overridable at runtime
    "fields":      list[dict],  # [{ "path": "skaters[].ppGoals", "label": "PP Goals", "type": "number" }]
    "notes":       str | None,
    "enabled":     bool
  }
  ```
- Exposed functions: `create()`, `list_all()`, `get()`, `update()`, `delete()`
- Writes to `triggers.json` after every mutation so triggers survive a restart

### `trigger_runner.py`
Called during the live audio pipeline, after `extract_entities()`.

- `match_triggers(text: str, triggers: list[TriggerRecord]) -> list[TriggerRecord]`:
  - For each enabled trigger, check if any keyword matches the transcript using the same fuzzy/LLM logic used for players and teams (RapidFuzz threshold ≥ 85 or LLM extraction)
  - Returns all matching triggers (may be multiple)
- `run_trigger(trigger: TriggerRecord) -> dict | None`:
  - Substitutes any `{param}` placeholders in the endpoint URL (from `path_params`)
  - Makes an async `httpx.AsyncClient` GET request
  - Walks the response JSON using each stored field path (dot notation + array index support)
  - Returns a `TriggerPayload` dict ready for broadcast
- `build_trigger_payload(trigger: TriggerRecord, values: dict) -> dict`:
  ```json
  {
    "type":        "trigger",
    "id":          "uuid",
    "keywords":    ["power play"],
    "description": "Show how many power play goals...",
    "fields": [
      { "label": "PP Goals",   "value": 24 },
      { "label": "First Name", "value": "Connor" },
      { "label": "Last Name",  "value": "McDavid" }
    ],
    "display": "power play · PP Goals: 24 | Connor McDavid"
  }
  ```

---

## Frontend Modules

### `useTriggers.ts`
- `getTriggers()` — `GET /triggers`
- `createTrigger(keywords, description)` — `POST /triggers` — returns the full resolved trigger including endpoint and fields for the user to review
- `toggleTrigger(id, enabled)` — `PATCH /triggers/{id}`
- `deleteTrigger(id)` — `DELETE /triggers/{id}`
- Loading and error states per operation

### `TriggerBuilder.tsx`
- Two inputs: **Keywords** (tag-style input, 1–3 words) and **Description** (free text)
- Submit calls `createTrigger` → shows a loading state ("Resolving endpoint…") during the LLM call
- On success: shows a **resolution preview** before saving:
  ```
  ✓ Endpoint found: GET /v1/club-stats/EDM/now
  Fields to display:
    · PP Goals       (skaters[].powerPlayGoals)
    · First Name     (skaters[].firstName)
    · Last Name      (skaters[].lastName)
  Notes: Sort skaters[] by powerPlayGoals desc for leaders.
  ```
- User can confirm (saves) or cancel (discards)
- On failure (no endpoint found): show inline error — "Could not find a matching endpoint. Try rephrasing your description."

### `TriggerList.tsx`
- Table/list of all saved triggers: keywords, description, resolved endpoint, enabled toggle, delete button
- Enabled toggle calls `toggleTrigger`
- Delete button calls `deleteTrigger` with a confirmation prompt

### `TriggerCard.tsx`
- Receives `TriggerPayload` from the WebSocket
- Renders the keyword(s) as a header badge, then each `{ label, value }` field pair
- Same slide-in + 8s auto-dismiss animation as `StatCard` and `TeamCard`
- Visual identity: purple/violet accent to distinguish custom triggers from built-in player/team cards

---

## Integration with Existing Pipeline

Changes to `server.py`:
- Add the four `/triggers` REST routes
- In the main audio pipeline, after `extract_entities()`, also call `trigger_runner.match_triggers()` and run any matched triggers concurrently with the existing player/team stat fetches
- Broadcast `TriggerPayload` objects alongside player/team payloads — the frontend already handles multiple `type` values

Changes to `OverlayCanvas.tsx`:
- Add `TriggerCard` to the routing switch alongside `StatCard` and `TeamCard`
- `type: "trigger"` → `<TriggerCard>`

---

## Tasks

### SETUP

- [ ] **TRIG-SETUP-01** — Create `backend/specs/` directory; copy or symlink the two NHL API spec files there as `api_spec_A.md` and `api_spec_B.md`
- [ ] **TRIG-SETUP-02** — Create `backend/triggers.json` as an empty object `{}` — this is the persistence file for saved triggers
- [ ] **TRIG-SETUP-03** — Add `uuid` to `backend/requirements.txt` if not already present (stdlib in Python 3.11, no install needed — just verify `import uuid` works)

---

### RESOLVER — `backend/trigger_resolver.py`

- [ ] **TRIG-RES-01** — Implement `load_spec_sections(spec_a: str, spec_b: str) -> list[dict]`:
  - Split each file on `##` / `###` headings via regex
  - Return flat list of `{ "source": filename, "heading": str, "body": str }`
  - Strip sections with body under 20 characters
- [ ] **TRIG-RES-02** — Implement `prefilter_sections(sections: list[dict], keywords: list[str], description: str, top_n: int = 8) -> list[dict]`:
  - Score by keyword + key-word-from-description overlap in heading (×3) and body (×1)
  - Return top-N; fall back to first N if all scores are 0
- [ ] **TRIG-RES-03** — Write the resolver system prompt as a module-level constant:
  - Specifies output JSON shape: `endpoint`, `method`, `path_params`, `fields[]` (path, label, type), `notes`
  - Explicitly forbids inventing fields not present in the provided sections
  - Specifies the `{ "endpoint": null, "error": "..." }` failure shape
- [ ] **TRIG-RES-04** — Implement `resolve_trigger(keywords: list[str], description: str) -> dict`:
  - Load sections → prefilter → build prompt → call Claude (`claude-sonnet-4-20250514`, `max_tokens=1000`)
  - Strip markdown fences, `json.loads()`, validate required keys
  - Return resolution dict or raise `ValueError` with the error string from Claude's failure response
- [ ] **TRIG-RES-05** — Manual smoke test: call `resolve_trigger` with 3 descriptions and print the result; verify endpoint URLs look valid and fields look plausible

---

### STORE — `backend/trigger_store.py`

- [ ] **TRIG-STORE-01** — Define `TriggerRecord` as a `TypedDict` matching the schema above
- [ ] **TRIG-STORE-02** — Implement `load_store() -> dict` and `save_store(store: dict)`: read from / write to `triggers.json`; initialize with `{}` if file missing or malformed
- [ ] **TRIG-STORE-03** — Implement `create_trigger(keywords, description, resolution) -> TriggerRecord`: merges user input + LLM resolution, assigns `uuid4` id, sets `enabled=True`, persists
- [ ] **TRIG-STORE-04** — Implement `list_triggers() -> list[TriggerRecord]`: returns all stored triggers
- [ ] **TRIG-STORE-05** — Implement `update_trigger(id: str, patch: dict) -> TriggerRecord | None`: applies partial update (used for enable/disable), persists
- [ ] **TRIG-STORE-06** — Implement `delete_trigger(id: str) -> bool`: removes by id, persists, returns `False` if id not found

---

### RUNNER — `backend/trigger_runner.py`

- [ ] **TRIG-RUN-01** — Implement `match_triggers(text: str, triggers: list[TriggerRecord], mode: str = "fuzzy") -> list[TriggerRecord]`:
  - For each enabled trigger, generate n-grams from transcript and RapidFuzz-match against trigger keywords (threshold ≥ 85)
  - Return all triggers with at least one keyword matched
- [ ] **TRIG-RUN-02** — Implement `extract_field_value(data: dict, path: str) -> any`:
  - Walk a JSON response using a dot-notation path with array support (e.g. `"skaters[0].powerPlayGoals"`)
  - Return `None` if path does not exist (never raise)
- [ ] **TRIG-RUN-03** — Implement `run_trigger(trigger: TriggerRecord) -> dict | None`:
  - Substitute `{param}` placeholders in endpoint URL using `trigger["path_params"]`
  - `httpx.AsyncClient` GET request with 5s timeout
  - For each stored field, call `extract_field_value` on the response JSON
  - Return `None` if HTTP error or timeout
- [ ] **TRIG-RUN-04** — Implement `build_trigger_payload(trigger: TriggerRecord, values: dict) -> dict`:
  - Assemble the `TriggerPayload` shape with `type: "trigger"`, keyword(s), field label/value pairs, and a `display` string
- [ ] **TRIG-RUN-05** — Unit test `match_triggers` with 4 cases:
  - Exact keyword match → trigger returned
  - Fuzzy match (misspelling) → trigger returned
  - Unrelated transcript → empty list
  - Disabled trigger → not returned even if keyword matches
- [ ] **TRIG-RUN-06** — Unit test `extract_field_value` with nested paths, array paths, and missing paths

---

### API ROUTES — `backend/server.py`

- [ ] **TRIG-API-01** — `POST /triggers`:
  - Body: `{ "keywords": list[str], "description": str }`
  - Calls `resolve_trigger` → `create_trigger`
  - Returns the full saved `TriggerRecord` (including resolved endpoint + fields) with `201`
  - Returns `422` with error message if resolver finds no matching endpoint
- [ ] **TRIG-API-02** — `GET /triggers`:
  - Returns `list[TriggerRecord]` with `200`
- [ ] **TRIG-API-03** — `PATCH /triggers/{id}`:
  - Body: `{ "enabled": bool }` (and any other patchable fields)
  - Returns updated `TriggerRecord` or `404`
- [ ] **TRIG-API-04** — `DELETE /triggers/{id}`:
  - Returns `204` on success, `404` if not found
- [ ] **TRIG-API-05** — Wire `trigger_runner` into the main audio pipeline in `main.py`:
  - After `extract_entities()` resolves, also call `match_triggers(text, list_triggers())`
  - For each matched trigger, `await run_trigger(trigger)` concurrently (use `asyncio.gather`)
  - `broadcast(build_trigger_payload(...))` for each result

---

### FRONTEND — `useTriggers.ts`

- [ ] **TRIG-FE-01** — Define TypeScript types:
  ```ts
  type TriggerField  = { path: string; label: string; type: string }
  type TriggerRecord = { id: string; keywords: string[]; description: string; endpoint: string; fields: TriggerField[]; notes: string | null; enabled: boolean }
  ```
- [ ] **TRIG-FE-02** — Implement `useTriggers()` hook:
  - `triggers`: `TriggerRecord[]` state, fetched from `GET /triggers` on mount
  - `createTrigger(keywords, description)`: `POST /triggers`, appends result to state; returns full record for preview
  - `toggleTrigger(id, enabled)`: `PATCH /triggers/{id}`, updates state in place
  - `deleteTrigger(id)`: `DELETE /triggers/{id}`, removes from state
  - `loading`: boolean, `error`: string | null

---

### FRONTEND — `TriggerBuilder.tsx`

- [ ] **TRIG-FE-03** — Build keyword tag input: type a word + press Enter/comma to add it; max 3 tags; remove tag with ×
- [ ] **TRIG-FE-04** — Build description textarea with a character limit (200 chars)
- [ ] **TRIG-FE-05** — Submit button calls `createTrigger`; show spinner + "Resolving endpoint…" label during the API call
- [ ] **TRIG-FE-06** — On success: render a **resolution preview panel** before final save:
  - Show resolved endpoint URL
  - List each field: label + JSON path
  - Show notes if present
  - Two buttons: **Save Trigger** (persists) and **Cancel** (discards without saving)
- [ ] **TRIG-FE-07** — On failure (resolver returns no endpoint): show inline error message; let user edit and retry
- [ ] **TRIG-FE-08** — On confirmed save: clear the form, close preview, and add the new trigger to `TriggerList`

---

### FRONTEND — `TriggerList.tsx`

- [ ] **TRIG-FE-09** — Render each trigger as a row: keywords (as badges), description (truncated), endpoint URL, enabled toggle, delete button
- [ ] **TRIG-FE-10** — Enabled toggle calls `toggleTrigger`; optimistic UI update
- [ ] **TRIG-FE-11** — Delete button shows a confirmation dialog before calling `deleteTrigger`
- [ ] **TRIG-FE-12** — Empty state: "No triggers yet. Create one above."

---

### FRONTEND — `TriggerCard.tsx`

- [ ] **TRIG-FE-13** — Create `TriggerCard` accepting props: `payload: TriggerPayload`, `onExpire: () => void`
- [ ] **TRIG-FE-14** — Style: keyword(s) as a purple/violet header badge; each `{ label, value }` field pair on its own line
- [ ] **TRIG-FE-15** — Reuse the same slide-in + fade-out animation as `StatCard`
- [ ] **TRIG-FE-16** — Auto-expire: `setTimeout(onExpire, 8000)` on mount

---

### FRONTEND — `OverlayCanvas.tsx` + `useOverlaySocket.ts`

- [ ] **TRIG-FE-17** — Add `TriggerPayload` to the `StatPayload` union type in `useOverlaySocket.ts`:
  ```ts
  type TriggerPayload = { type: "trigger"; id: string; keywords: string[]; fields: { label: string; value: any }[]; display: string }
  type StatPayload    = PlayerPayload | TeamPayload | TriggerPayload
  ```
- [ ] **TRIG-FE-18** — Add `type === "trigger"` case to `OverlayCanvas`'s card router → renders `<TriggerCard>`

---

### INTEGRATION & TESTS

- [ ] **TRIG-INT-01** — Integration test: create a trigger via `POST /triggers` with a real description, verify the stored record has a non-null endpoint and at least one field
- [ ] **TRIG-INT-02** — Integration test: simulate a transcript match, verify `run_trigger` returns a non-null payload with populated field values
- [ ] **TRIG-INT-03** — End-to-end test: create a trigger from the frontend UI, speak the keyword into the mic (or feed a test audio file), verify a `TriggerCard` appears on the overlay
- [ ] **TRIG-INT-04** — Verify disabled triggers are never matched during live audio even if keyword is present in transcript
- [ ] **TRIG-INT-05** — Verify triggers persist across a backend restart (loaded from `triggers.json` on startup)

---

## Task Summary

| Area | Tasks |
|---|---|
| Setup | TRIG-SETUP-01 → 03 |
| Resolver | TRIG-RES-01 → 05 |
| Store | TRIG-STORE-01 → 06 |
| Runner | TRIG-RUN-01 → 06 |
| API routes | TRIG-API-01 → 05 |
| Frontend hook | TRIG-FE-01 → 02 |
| TriggerBuilder | TRIG-FE-03 → 08 |
| TriggerList | TRIG-FE-09 → 12 |
| TriggerCard | TRIG-FE-13 → 16 |
| Overlay wiring | TRIG-FE-17 → 18 |
| Integration | TRIG-INT-01 → 05 |

---

## Out of Scope (MVP)

- Editing a trigger's description or keywords after creation (delete + recreate instead)
- Multiple field extraction strategies (e.g. aggregate, filter, sort) — MVP extracts raw field values only
- Trigger ordering or priority when multiple triggers match simultaneously
- Persistent trigger history / audit log

---

## Post-MVP Ideas

### LLM-Generated Card HTML

Instead of every trigger rendering through the same generic `TriggerCard` layout, a second LLM call at creation time could generate a custom HTML template for each trigger. A "Power Play Goals" card could look visually distinct from a "Save Percentage" card — different layout, accent color, and field emphasis — all reflecting the trigger's description.

#### How it would work

At trigger creation, `trigger_resolver.py` makes a second call after endpoint resolution, asking the LLM to produce a self-contained HTML snippet styled with the overlay's existing Tailwind classes. The template uses `{{Label}}` placeholder tokens (where `Label` matches a `field.label` value exactly) that get replaced with live data at render time.

The resolver prompt would need to supply:
- The Tailwind utility classes already used in `StatCard` and `TeamCard` — so the LLM works within the existing design system rather than inventing classes that don't exist in the build
- Hard broadcast constraints: dark background, minimum readable font size, max card width
- The trigger's keywords and description as creative context
- An example input/output pair to lock in the expected format

The generated template is stored as `html_template` in `TriggerRecord` alongside the existing fields.

#### Open question 1 — filling in dynamic data at runtime

**Option A (recommended): frontend substitution**
The frontend fetches the full `TriggerRecord` list on load via `GET /triggers` and caches the templates. When a `TriggerPayload` arrives over the WebSocket, `TriggerCard` looks up the template by `trigger.id`, replaces each `{{field.label}}` token with the corresponding `field.value` from the payload, and renders the result. The backend never touches HTML strings at runtime.

**Option B: backend substitution**
The backend fills the template before broadcast and sends the completed HTML as a `html` field on `TriggerPayload`. Simpler for the frontend, but Python is now doing string manipulation on LLM-generated HTML on every trigger fire.

#### Open question 2 — HTML flow from backend to frontend

- `POST /triggers` response adds `html_template: string | null` to the returned `TriggerRecord`
- The `useTriggers` hook stores it alongside the other trigger fields
- `TriggerCard` checks: if `triggers[id].html_template` is present, substitute tokens and render via `dangerouslySetInnerHTML`; otherwise fall back to the generic field-list layout

> **XSS:** the HTML comes from an LLM prompted by the user's own description, so the surface is limited to self-XSS. Still worth running the output through a sanitizer (e.g. DOMPurify) before passing to `dangerouslySetInnerHTML`.

---

## Post-MVP: Advanced Trigger Capabilities

Three complementary enhancements that build on the MVP trigger system. They are designed to be additive — each can ship independently, and together they enable triggers that are contextual, sequential, and composable.

---

### 1. Contextual Input Slots

**What it enables:** A trigger can declare typed "slots" — named placeholders filled at runtime from entities already extracted by the audio pipeline. This lets a single trigger fire for any team or player rather than being hardcoded to a specific one (e.g. `<team> power play` works for EDM, TOR, or anyone).

**Example:** Keyword pattern `<team> power play` — when the transcript says "Edmonton power play", the `<team>` slot is filled with `EDM` before the endpoint is called.

#### Data model change

Add `input_slots` to `TriggerRecord`:
```python
"input_slots": [
  { "name": "team",   "type": "team",   "required": True },   # fills from extract_entities()["teams"]
  { "name": "player", "type": "player", "required": False }    # fills from extract_entities()["players"]
]
```
- `"team"` slots receive 3-letter abbreviations — exactly what `extract_entities()["teams"]` returns
- `"player"` slots receive canonical full names — exactly what `extract_entities()["players"]` returns
- `path_params` values already support `{param}` substitution; slots just make those values dynamic rather than static

#### Prompt change

Extend the resolver system prompt with:
```
If the user's description requires a dynamic entity (a specific team or player resolved
from the live transcript), declare it as an input slot in "input_slots".
Use {slot_name} as the placeholder in the endpoint URL and in path_params.
Slot types: "team" → 3-letter team abbreviation (e.g. "EDM"),
            "player" → canonical player full name (e.g. "Connor McDavid").
If no dynamic entity is needed, return "input_slots": [].
```

#### Logic changes

- `match_triggers(text, triggers, extracted)` receives the already-computed `extracted` dict from the pipeline — no extra extraction call needed
- A trigger only fires if: keyword fuzzy match passes **and** all `required=True` slots have a candidate in `extracted`; if a required slot has no match, the trigger is skipped for this transcript
- Filled slot values are passed to `run_trigger(trigger, slot_values={})` and merged into `path_params` before URL substitution

**`TriggerBuilder.tsx`:** Allow `<slot_name>` syntax in the keyword tag input. Resolution preview shows declared slots: `Requires: <team> (team abbreviation)`.

---

### 2. Chained Endpoint Operations

**What it enables:** A trigger executes a **sequence of HTTP calls** where each step can extract intermediate values (e.g. a player ID from a search) and inject them as path parameters into the next step. This is necessary when the desired data requires a lookup before the main fetch.

**Example:**
- Step 1: `GET /search/player?q={player}` → extract `playerId` from response
- Step 2: `GET /player/{playerId}/landing` → display PP Goals

#### Data model change

Replace the MVP top-level `endpoint` / `fields` with a `steps` list. Only the final step declares display `fields`; intermediate steps declare `extract` (variables forwarded to subsequent steps):

```python
# Intermediate step — extracts variables for downstream steps
{
  "type":        "endpoint",
  "endpoint":    "https://search.d3.nhle.com/api/v1/search/player?q={player}&active=true",
  "method":      "GET",
  "path_params": { "player": "{player}" },        # slot value or prior-step variable
  "extract":     { "playerId": "0.playerId" }      # varName → dot-notation path in response
}

# Final step — display fields; no extract
{
  "type":        "endpoint",
  "endpoint":    "https://api-web.nhle.com/v1/player/{playerId}/landing",
  "method":      "GET",
  "path_params": { "playerId": "{playerId}" },     # variable from step 1
  "fields": [
    { "path": "featuredStats.regularSeason.subSeason.powerPlayGoals",
      "label": "PP Goals", "type": "number" }
  ]
}
```

Variables declared in a step's `extract` are available as `{varName}` in all subsequent steps.

#### Prompt change

Replace the single-endpoint resolver prompt with a steps-aware version:
```
If a single endpoint satisfies the description, return a one-item "steps" array.
If the data requires a preliminary lookup (e.g. resolving a player name to an ID
before fetching stats), return multiple steps in order.

Each step:
  - "type": "endpoint"
  - "endpoint": full URL with {param} placeholders
  - "method": "GET"
  - "path_params": { "param": static_value_or_"{variable}" }
  - "extract": { "varName": "dot.path.in.response" }  ← intermediate steps only
  - "fields": [...]                                    ← final step only

Variables declared in "extract" are available as {varName} in all later steps.
Respond with "steps": [...] instead of a top-level "endpoint" and "fields".
```

#### Logic changes

`run_trigger` becomes a sequential step executor with a shared `context` dict. `endpoint` and `trigger_ref` steps can appear in any order — including as the final step:

```python
async def run_trigger(trigger, slot_values={}):
    context = dict(slot_values)
    steps   = trigger["steps"]
    for i, step in enumerate(steps):
        is_last = (i == len(steps) - 1)

        if step["type"] == "endpoint":
            url  = substitute(step["endpoint"], {**step["path_params"], **context})
            data = await http_get(url)       # returns None on timeout/error → abort chain
            if data is None:
                return None
            if is_last:
                values = {f["label"]: extract_field_value(data, f["path"]) for f in step["fields"]}
                return build_trigger_payload(trigger, values)
            else:
                for var, path in step.get("extract", {}).items():
                    context[var] = extract_field_value(data, path)

        elif step["type"] == "trigger_ref":
            ref = get_trigger(step["trigger_id"])
            if ref is None:
                return None                  # referenced trigger deleted — abort chain
            ref_payload = await run_trigger(ref, context)
            if ref_payload is None:
                return None
            if is_last:
                # final step: inherit the ref's display fields under this trigger's identity
                return build_trigger_payload(trigger, {f["label"]: f["value"] for f in ref_payload["fields"]})
            else:
                for var, label in step.get("extract", {}).items():
                    match = next((f for f in ref_payload["fields"] if f["label"] == label), None)
                    context[var] = match["value"] if match else None
```

> **Single broadcast guarantee:** `run_trigger` returns a payload exactly once — only when `is_last == True` for the final step. The server pipeline calls `broadcast()` only on `run_trigger`'s return value. Intermediate steps accumulate silently into `context`. No card is emitted mid-chain.
>
> Same guarantee applies to `trigger_ref` intermediate steps: the `ref_payload` is consumed locally to populate `context`; it is **not** re-broadcast.

Steps can be freely mixed in any order: `endpoint → trigger_ref → endpoint → trigger_ref` is valid. Each step type can appear anywhere — the only invariant is that by the time a step runs, all `{variables}` it references must already be in `context`.

**Backward compatibility:** At load time, if a stored trigger has a top-level `endpoint` (MVP shape), wrap it in a single-item `steps` list transparently — no migration needed.

---

### 3. Trigger Composition (Trigger-as-Step)

**What it enables:** A step in a chain can be a `trigger_ref` — a reference to an existing saved trigger. The LLM resolver receives a summary of all saved triggers and can reuse them as sub-sequences rather than re-deriving raw endpoints (e.g. always using a "resolve player name to ID" trigger as step 1 instead of re-specifying the search endpoint from scratch).

#### Data model change

Add a second step type alongside `"endpoint"`:
```python
{
  "type":       "trigger_ref",
  "trigger_id": "abc123",                         # id of the referenced trigger
  "extract":    { "playerId": "Player ID" }        # varName → field label from that trigger's output
}
```
The referenced trigger's output field values become available as `{varName}` in all subsequent steps.

#### Prompt change

The resolver receives a **trigger library summary** injected before the API spec sections:
```
## Saved Triggers (available as reusable steps)
[
  {
    "id": "abc123",
    "description": "Resolve player name to NHL player ID",
    "input_slots": [ { "name": "player", "type": "player", "required": true } ],
    "output_fields": ["Player ID", "Full Name"]
  },
  {
    "id": "def456",
    "description": "Get team power play stats",
    "input_slots": [ { "name": "team", "type": "team", "required": true } ],
    "output_fields": ["PP Goals", "PP Opportunities", "PP%"]
  },
  ...
]

If an existing trigger already covers a sub-task you need (e.g. resolving a name to an ID),
prefer a "trigger_ref" step over duplicating endpoint logic.
A "trigger_ref" step exposes the referenced trigger's output field values as variables
via its "extract" mapping: { "varName": "Field Label" }.
Before using a trigger_ref, verify that all of its required input_slots are already
present in the chain's context (filled by a slot or extracted by a prior step).
```

`trigger_resolver.py` injects this section at call time by calling `trigger_store.list_triggers()` and formatting summaries (id, description, input_slots, output field labels). Output field labels are derived from the trigger's final step's `fields[].label` values.

#### Logic changes

Add a `trigger_ref` branch to the step executor in `run_trigger`:
```python
elif step["type"] == "trigger_ref":
    ref = get_trigger(step["trigger_id"])
    if ref is None:
        return None                               # referenced trigger deleted — abort chain
    ref_payload = await run_trigger(ref, context)
    if ref_payload is None:
        return None
    for var, label in step.get("extract", {}).items():
        match = next((f for f in ref_payload["fields"] if f["label"] == label), None)
        context[var] = match["value"] if match else None
```

**`TriggerList.tsx`:** Show a dependency badge on triggers referenced by others ("used by 2 triggers"). Warn before deletion: "2 other triggers depend on this one. Delete anyway?"

**`TriggerBuilder.tsx` resolution preview:** When `trigger_ref` steps are present, show the referenced trigger's description: `Step 1: uses saved trigger "Resolve player name to ID"`.

---

### Combined example

User creates: keyword `<player> power play`, description "Show that player's power play goals this season."

- Input slot: `player` (required, filled from `extract_entities()["players"]`)
- Step 1: `trigger_ref` → "Resolve player name to ID" → extracts `playerId` from `Player ID` field
- Step 2: `endpoint` → `GET /player/{playerId}/landing` → fields: PP Goals

At runtime, transcript contains "McDavid power play":
1. Slot `player` = `"Connor McDavid"` (from extractor, no extra LLM call)
2. Trigger keyword matches + required slot filled → trigger fires
3. Step 1: referenced trigger runs → `context["playerId"] = 8478402`
4. Step 2: calls `/player/8478402/landing` → `PP Goals: 24`
5. TriggerCard renders: `power play · PP Goals: 24`

---

## Future Ideas (not planned, not scoped)

> These are directions the trigger system *could* grow in. None are scheduled. Document them here so the ideas aren't lost, not because they're next.

---

### Array operations

The biggest practical gap: NHL API responses are full of arrays (`skaters[]`, `games[]`, `goalies[]`) and the chain can only grab a value at a fixed index today. Three primitives that cover most cases:

- **Filter** — keep only elements matching a condition: `skaters[] where playerId == {playerId}`
- **Sort + take** — order by a field and slice: `skaters[] sorted by powerPlayGoals desc, take 3`
- **Aggregate** — reduce an array to a scalar: `sum(skaters[].goals)`, `avg(lines[].corsi)`

Stored as a `transform` field on an intermediate or final step. The runner evaluates them as plain array operations — no expression engine needed, just a small set of known operations.

---

### Computed display fields

Derive new values from already-extracted ones before display. Examples:
- `goals / games_played` → goals per game
- `"{firstName} {lastName}"` → combined name from two separate fields
- `savePercentage * 100` → save percentage as a readable number

Stored as a `compute` block in the final step alongside `fields`:
```python
{ "label": "GPG", "expr": "goals / games_played", "round": 2 }
```
The runner evaluates the expression against the extracted field values, no LLM involved at runtime.

---

### Conditional branching

Route to a different step based on a context variable. Most immediate use case: a player could be a skater or a goalie — the right stats endpoint differs. A `condition` step checks a value and jumps to one of two named branches.

Without this, a trigger that needs to handle both player types requires two separate triggers.

---

### Parallel fan-out

A `parallel` step fires multiple sub-chains simultaneously and merges their outputs before the next step continues. Useful for comparisons: fetch two players' stats at the same time and display both on a single combined card. Maps naturally onto `asyncio.gather`.

---

### Per-trigger result caching

The built-in player and team stats have a 45-second cache. Custom trigger chains have none — if a keyword fires twice in 10 seconds the full chain runs twice. A `(trigger_id, slot_values_hash)` → cached result TTL solves this. Cache duration configurable per trigger at creation time, defaulting to `NHL_CACHE_TTL`.

---

### Composite keyword logic

Today keywords are OR'd — any one match fires the trigger. Two additions:
- **AND** — multiple keywords must all appear in the same transcript segment
- **NOT** — fire on `"penalty"` but not if `"power play"` is also present

Stored as a `keyword_logic` field on `TriggerRecord`: `"and"`, `"or"` (default), or a list of exclusion terms.

---

### Threshold-gated firing

A trigger only broadcasts if an extracted value passes a condition. Example: a "hot streak" card only appears if `goals_last_5_games > 2`. The gate is evaluated after the final step, before `build_trigger_payload` — if it fails, the chain ran silently and nothing is shown.

Stored as a `fire_if` field on `TriggerRecord`: `{ "field": "Goals (Last 5)", "op": ">", "value": 2 }`.

---

### Multi-card output

A single trigger broadcasts multiple cards. Example: "show the top line's stats" → three separate player cards. The final step returns a list of payloads instead of one. The runner iterates and broadcasts each. The existing `asyncio.gather` pattern in the pipeline handles this with no structural change — each payload is already an independent broadcast.
