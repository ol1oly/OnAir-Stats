# Settings & Navigation Design

> Design decisions for the 3-page app structure and the settings panel.
> Date: 2026-04-02

---

## Pages

Hash-based routing (`#/`) — no server config required, works in OBS browser source and in a regular browser tab.

| Route | Purpose |
|---|---|
| `#/` | **Landing** — app title, mic status, start/stop button, links to Settings and Overlay |
| `#/overlay` | **OBS overlay** — transparent, no UI chrome; this is what the OBS browser source URL points to |
| `#/settings` | **Settings panel** — all tunable knobs with descriptions |

`App.tsx` becomes the router shell. The overlay page is the current `App.tsx` content (OverlayCanvas + MicHud). The landing page is a new control panel. Settings is a new form page.

Router choice: `wouter` with hash mode, or a minimal hand-rolled `useHashLocation` — either avoids a server config requirement.

---

## Settings Controls

### Deepgram Model — slider, 3 stops

| Label | Value | Description |
|---|---|---|
| Fast | `nova` | Slightly lower accuracy, minimal latency. Good for fast-paced play-by-play. |
| **Balanced** *(default)* | `nova-2` | Best accuracy/latency tradeoff. Recommended for most broadcasts. |
| Whisper | `whisper-large` | Highest accuracy, higher latency (~2–3s). Best for slower commentary or review shows. |

Backend param: `DEEPGRAM_MODEL`

---

### Broadcast Language — slider, 2 stops

| Label | Value |
|---|---|
| English | `en` |
| French | `fr` |

Backend param: `DEEPGRAM_LANGUAGE`. Changing this requires a transcriber restart (~1–2s downtime). See the EN/FR debate section below.

---

### Name Matching Sensitivity — slider, 4 stops

Controls how strictly spoken words must match player/team names. Moves `FUZZY_NGRAM_THRESHOLD` and `FUZZY_PARTIAL_THRESHOLD` together.

| Label | Ngram / Partial | Description |
|---|---|---|
| Strict | 90 / 96 | Fewest false positives. May miss unusual pronunciations. |
| **Balanced** *(default)* | 82 / 90 | Current defaults. Good for clear audio. |
| Relaxed | 72 / 82 | More matches, occasional false positives on similar names. |
| Open | 62 / 74 | Maximum recall. Useful for noisy audio or accented commentary. |

Backend params: `FUZZY_NGRAM_THRESHOLD`, `FUZZY_PARTIAL_THRESHOLD`

---

### Stats Cache — slider, 4 stops

How long player/team stats are kept in memory before re-fetching from the NHL API.

| Label | TTL | Description |
|---|---|---|
| Live | 15s | Always fresh. Higher API usage. Best during active games. |
| **Default** *(default)* | 45s | Good balance for in-game use. |
| Relaxed | 120s | Fewer API calls. Fine for pre-game or slow periods. |
| Static | 300s | Minimal API usage. Suitable for recording/replay scenarios. |

Backend param: `NHL_CACHE_TTL`

---

### Card Display Duration — slider, 4 stops *(frontend only)*

| Label | ms | Description |
|---|---|---|
| Brief | 5000 | Cards leave quickly. Less screen clutter. |
| **Default** *(default)* | 8000 | Current default. |
| Extended | 12000 | More time to read. Good for complex goalie stats. |
| Persistent | 20000 | Cards linger. Useful for highlight reels or paused review. |

Frontend param: `CARD_DISPLAY_MS` — stored in localStorage only, never sent to backend.

---

### Max Visible Cards — slider, 3 stops *(frontend only)*

| Label | Value | Description |
|---|---|---|
| 1 | 1 | Clean, single-card focus. |
| **3** *(default)* | 3 | Current default. |
| 5 | 5 | For wide overlays or multi-monitor setups. |

Frontend param: `MAX_CARDS` — localStorage only.

---

## Local Storage Strategy

**Rule: read once on init, write on change.**

1. On app init, a `SettingsContext` loads all settings from `localStorage` in a single pass into memory.
2. All components read from the in-memory context — never from `localStorage` directly.
3. On any setting change, write only that key to `localStorage` (synchronous; settings changes are infrequent).
4. On init, after loading from storage, POST the backend-bound settings once to sync the server.
5. No polling or periodic re-read of `localStorage`.

Result: 1 localStorage read per page load, 1 backend POST per page load, 1 localStorage write per change.

---

## Passing Settings to the Backend

**Approach: `POST /settings` endpoint.**

The frontend sends only the backend-relevant keys:
```json
{
  "language": "fr",
  "model": "nova-2",
  "fuzzy_ngram_threshold": 82,
  "fuzzy_partial_threshold": 90,
  "cache_ttl": 45.0
}
```

The backend updates a runtime settings dict (separate from `config.py`, which stays as the cold-start defaults). Frontend-only settings (`CARD_DISPLAY_MS`, `MAX_CARDS`) are never sent.

**Effect per setting:**
- `cache_ttl`, `fuzzy_*` — take effect immediately on next lookup/match.
- `language` or `model` — require restarting the Deepgram transcriber: stop current instance, create new one with updated params, start it. ~1–2s downtime, acceptable for a settings change.

**Backend persistence:** the server does NOT persist settings to disk. On restart it reverts to `config.py` defaults. The frontend re-POSTs on next page load (from localStorage), so settings are effectively persisted client-side.

---

## EN/FR: One Transcriber or Two?

### Case for two simultaneous transcribers
- Some markets (Montreal, Ottawa) have genuinely bilingual broadcasts.
- Parallel EN+FR transcription would catch mentions in either language without a manual switch.

### Case for one transcriber *(chosen)*
- **Cost:** two concurrent Deepgram WebSocket connections doubles API usage at all times, even for monolingual broadcasts.
- **Audio routing:** the browser sends one audio stream. Duplicating it to two WebSocket connections adds complexity with no benefit when the broadcast is monolingual.
- **Accuracy:** `nova-2` with `language: "fr"` is already accurate for French hockey commentary — a second instance adds nothing over a correctly configured single one.
- **Switching is fast:** tearing down and restarting the Deepgram WS on a language change takes ~1–2s — fine for a settings change made before a broadcast starts.
- **Bilingual edge case:** if bilingual support is ever needed, the right tool is Deepgram's `multi-language` detection feature (single connection, automatic language detection) — not two parallel instances.

**Decision: one transcriber. Language is a runtime-switchable setting via `POST /settings`.**
