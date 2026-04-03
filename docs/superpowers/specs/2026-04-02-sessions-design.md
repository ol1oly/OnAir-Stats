# Sessions Feature Design

> Multi-user shared overlay sessions for NHL Radio Overlay.
> Date: 2026-04-02

---

## Context

Currently all overlay clients connected to `/ws` receive every broadcast — there is no isolation between users. This design adds **sessions**: a short-code room that scopes both audio input and stat card output to a group of users. Anyone in the same session hears the same commentary and sees the same cards. Anyone can broadcast audio.

---

## Decisions

| Question | Decision |
|---|---|
| Session identification | Random 4-char code (e.g. `XK7F`), server-generated |
| Session lifetime | Ephemeral — deleted when last member disconnects |
| Audio | All members can broadcast mic audio |
| Session UI (now) | Splash screen gates the overlay on load |
| Session UI (future) | Move to `#/` landing page once `settings-design.md` routing is built |
| Session code visibility | Always visible in MicHud |
| Participant count | Live count shown in MicHud |
| Lock | Creator can lock/unlock; no new members can join while locked |
| Creator transfer | When creator disconnects, oldest remaining member becomes creator |
| Solo use | Clicking "New Session" always works — you can be alone in a session |

---

## Backend

### Session store (`backend/server.py` or `backend/session_store.py`)

```python
@dataclass
class Session:
    code: str
    ws_clients: list[WebSocket]   # ordered by join time; index 0 = creator
    audio_clients: set[WebSocket]
    locked: bool = False
    created_at: float = field(default_factory=time.time)

sessions: dict[str, Session] = {}
```

`ws_clients` is a **list** (not a set) to preserve join order. `ws_clients[0]` is always the current creator. On disconnect, if the departing client was `ws_clients[0]`, the next oldest member (`ws_clients[1]` after removal) becomes creator automatically — no extra state needed.

### New endpoints

| Endpoint | Purpose | Response |
|---|---|---|
| `POST /session` | Create session, return code | `{code: "XK7F"}` |
| `GET /session/{code}` | Check if joinable | `{exists: bool, locked: bool, participant_count: int}` |
| `WS /ws?session=CODE` | Overlay subscriber; first joiner is creator | existing envelope |
| `WS /audio?session=CODE` | Audio sender (mic blobs) | binary only |

`POST /session` generates a collision-safe code using `SESSION_CODE_LENGTH` and `SESSION_CODE_CHARS` from `config.py`. If the generated code already exists, regenerate.

### Session-scoped broadcast

Replace the global `_ws_clients: set` and `_broadcast()` with:

```python
async def _broadcast_to_session(code: str, payload: dict) -> None
```

Each audio WS handler already knows its session code from the query param — it passes the code when calling broadcast.

### Lock / unlock (via WS message)

The `/ws` handler currently ignores all incoming messages. Change it to parse JSON frames and handle:

```json
{"type": "session_lock", "locked": true}
{"type": "session_lock", "locked": false}
```

Server checks `sender == session.ws_clients[0]` (current creator). If valid, sets `session.locked` and broadcasts a system event to all members.

### New system events

All use `payload.type = "system"`. New `event` values:

| Event | Payload additions | Recipients |
|---|---|---|
| `session_joined` | `participant_count: int` | all in session |
| `session_left` | `participant_count: int` | remaining members |
| `session_locked` | `locked: true` | all in session |
| `session_unlocked` | `locked: false` | all in session |
| `session_rejected` | `reason: "locked" \| "not_found"` | rejected client only |
| `session_creator_changed` | `is_creator: true` | new creator only |

`session_rejected` is sent before closing the WS connection when a client tries to join a locked or nonexistent session. `session_creator_changed` is sent only to the newly promoted creator (targeted send, not broadcast) immediately after the `session_left` broadcast.

### Config additions (`backend/config.py`)

```python
# Sessions
SESSION_CODE_LENGTH = 4
SESSION_CODE_CHARS = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"  # unambiguous chars only
```

---

## Frontend

### New: `frontend/src/components/SessionSplash.tsx`

Fullscreen centered UI shown before any session is active. Replaced by the overlay once connected.

- Text input: auto-uppercase, max length = `SESSION_CODE_LENGTH`, letter-spacing for readability
- "Join" button: disabled until input is full-length; calls `GET /session/{code}` first, then `joinSession(code)`
- "New Session" button: calls `createSession()` immediately
- Inline error: shown if session not found or locked (`session_rejected` system event or non-200 GET response)

### New: `frontend/src/hooks/useSession.ts`

Owns all session state. Consumed by `App.tsx` and `MicHud.tsx`.

```typescript
interface UseSessionReturn {
  sessionCode: string | null
  isCreator: boolean
  isLocked: boolean
  participantCount: number
  joinSession(code: string): Promise<void>
  createSession(): Promise<void>
  setLocked(locked: boolean): void   // sends WS message; creator only
}
```

- `createSession()`: calls `POST /session`, stores code, sets `isCreator = true`
- `joinSession(code)`: calls `GET /session/{code}`, rejects if locked/not found, else stores code
- `isCreator`: derived from whether the client's WS is `ws_clients[0]` — backend confirms via `session_joined` system event including `is_creator: bool`
- `participantCount` and `isLocked`: updated reactively from `session_*` system events forwarded by `useOverlaySocket`

### Modified: `frontend/src/hooks/useOverlaySocket.ts`

- Accept `sessionCode: string | null` param; build URL as `/ws?session=CODE`
- Don't connect if `sessionCode` is null
- Forward `session_*` system events (currently only `connected`/`disconnected` are handled)

### Modified: `frontend/src/hooks/useMicCapture.ts`

- Accept `sessionCode: string | null` param; build URL as `/audio?session=CODE`
- Don't connect if `sessionCode` is null

### Modified: `frontend/src/components/MicHud.tsx`

Gains a session panel between the connection indicator and the mic button:

```
● Connected
┌─────────────────────────┐
│ SESSION          👥 3   │
│ XK7F             🔓/🔒  │  ← lock icon only for creator
└─────────────────────────┘
■ Stop
```

- Session code: click to copy to clipboard
- `🔓` (creator only): click to lock; sends `session_lock` WS message
- `🔒`: shown to all when locked; creator can click to unlock
- Non-creator sees static `🔒` indicator (no click action) when session is locked

### Modified: `frontend/src/App.tsx`

```tsx
const session = useSession()

if (!session.sessionCode) return <SessionSplash session={session} />
return (
  <>
    <OverlayCanvas latestPayload={latestPayload} />
    <MicHud session={session} ... />
  </>
)
```

WS URLs are passed to hooks only once `sessionCode` is set.

### Modified: `frontend/src/types/payloads.ts`

Extend `SystemPayload.event` union:

```typescript
event:
  | 'connected' | 'disconnected' | 'transcriber_ready' | 'transcriber_error'
  | 'session_joined' | 'session_left'
  | 'session_locked' | 'session_unlocked'
  | 'session_rejected' | 'session_creator_changed'

// Additional optional fields on SystemPayload:
participant_count?: number
is_creator?: boolean
locked?: boolean
reason?: 'locked' | 'not_found'
```

### Config additions (`frontend/src/config.ts`)

```typescript
export const SESSION_CODE_LENGTH = 4
```

---

## Data Flow Summary

```
User: "New Session"
  → POST /session → {code: "XK7F"}
  → WS /ws?session=XK7F  (creator = ws_clients[0])
  → WS /audio?session=XK7F
  → system: session_joined, participant_count:1, is_creator:true
  → Splash hidden, overlay shown

User 2: enters "XK7F" → Join
  → GET /session/XK7F → {exists:true, locked:false}
  → WS /ws?session=XK7F
  → WS /audio?session=XK7F
  → system: session_joined, participant_count:2 → broadcast to all

Any member speaks:
  → /audio?session=XK7F → transcriber → extractor → stats
  → _broadcast_to_session("XK7F", payload)
  → all /ws?session=XK7F clients receive stat card

Creator disconnects:
  → ws_clients[0] removed → ws_clients[1] is new creator
  → broadcast: system: session_left, participant_count:N-1
  → targeted: system: session_creator_changed, is_creator:true → new creator only

Last member disconnects:
  → session deleted from store
```

---

## Files Changed

| File | Type |
|---|---|
| `backend/server.py` | Modified — SessionStore, new endpoints, session-scoped broadcast, WS lock handler |
| `backend/config.py` | Modified — SESSION_CODE_LENGTH, SESSION_CODE_CHARS |
| `frontend/src/App.tsx` | Modified — session gate |
| `frontend/src/hooks/useOverlaySocket.ts` | Modified — session-aware URL, forward session events |
| `frontend/src/hooks/useMicCapture.ts` | Modified — session-aware URL |
| `frontend/src/components/MicHud.tsx` | Modified — session panel |
| `frontend/src/config.ts` | Modified — SESSION_CODE_LENGTH |
| `frontend/src/types/payloads.ts` | Modified — new system event values |
| `frontend/src/components/SessionSplash.tsx` | **New** |
| `frontend/src/hooks/useSession.ts` | **New** |
| `docs/superpowers/specs/2026-04-02-sessions-design.md` | **New** (this file) |
| `docs/README.md` | Modified — add entry |

---

## Future Work (out of scope for this spec)

- Move session join/create UI to `#/` landing page (see `settings-design.md`)
- Persist session preference in `localStorage` so page reload rejoins the same session if still active
- Session list or QR code share
