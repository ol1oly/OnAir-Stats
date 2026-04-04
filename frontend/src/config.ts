/**
 * Centralized configuration for the NHL Radio Overlay frontend.
 *
 * Edit values here to tune the overlay's look and behaviour.
 * Tailwind visual classes (colors, sizes) stay inline in each component.
 *
 * IMPORTANT: Any new tunable constant (timeout, limit, interval, URL,
 * batch size) MUST be added here — never hardcoded inline in a module.
 */

// ---------------------------------------------------------------------------
// Connection — where the frontend connects to the backend
// ---------------------------------------------------------------------------

// WebSocket that receives stat-card payloads to display on the overlay
export const WS_OVERLAY_URL = 'ws://localhost:8000/ws'

// WebSocket that streams mic audio to the backend for transcription
export const WS_AUDIO_URL = 'ws://localhost:8000/audio'

// ---------------------------------------------------------------------------
// Overlay behaviour
// ---------------------------------------------------------------------------

// Maximum number of stat cards visible on screen at once (oldest is dropped when exceeded).
// Runtime value comes from SettingsContext (localStorage). This is the default.
export const MAX_CARDS = 3

// If the same player/team is mentioned again within this window (ms), ignore the duplicate
export const DEDUP_MS = 2000

// How long (ms) a stat card stays on screen before sliding out.
// Runtime value comes from SettingsContext (localStorage). This is the default.
export const CARD_DISPLAY_MS = 8000

// Duration (ms) of the slide-out/fade animation when a card is dismissed
export const CARD_EXIT_MS = 200

// ---------------------------------------------------------------------------
// Mic capture
// ---------------------------------------------------------------------------

// How often (ms) the browser batches and sends audio to the backend
// Lower = less latency but more WebSocket messages; 250 is a good balance
export const MIC_TIMESLICE_MS = 250

// ---------------------------------------------------------------------------
// WebSocket reconnection
// ---------------------------------------------------------------------------

// Delay sequence (ms) between reconnection attempts — cycles through then stays at the last value
export const WS_BACKOFF_MS = [1000, 2000, 4000, 5000]

// How long (ms) to wait before auto-reconnecting the /audio WebSocket after an unexpected close
// (e.g. backend restart after a settings change). Long enough for the server to be ready.
export const AUDIO_WS_RECONNECT_DELAY_MS = 1500
