# NHL Radio Overlay — Frontend Design Spec

An OBS browser source overlay (1920x1080, transparent background) that receives stat payloads over WebSocket and renders animated cards in the bottom-left corner of the screen.

For payload shapes and TypeScript types, see [`docs/api/ws-payload-contract.md`](api/ws-payload-contract.md).

---

## File Structure

```
frontend/src/
  main.tsx                              root — transparent full-screen canvas
  index.css                             global styles + animation keyframes
  types/
    payloads.ts                         TypeScript types (from ws-payload-contract.md)
  hooks/
    useMicCapture.ts                    mic capture + binary WS to /audio
    useOverlaySocket.ts                 WS /ws connection + payload parsing
  components/
    OverlayCanvas.tsx                   card queue manager + type router
    StatCard.tsx                        skater stat card
    GoalieCard.tsx                      goalie stat card
    TeamCard.tsx                        team stat card
    TriggerCard.tsx                     custom trigger card              (post-MVP)
    TriggerBuilder.tsx                  trigger creation form            (post-MVP)
    TriggerList.tsx                     trigger management list          (post-MVP)
    FieldConfigPanel.tsx                stat field configuration         (post-MVP)
    StandingsCard.tsx                   multi-team standings table       (post-MVP)
```

---

## Design Language

### Color Palette

| Element | Color | Tailwind |
|---|---|---|
| Card background | 80% opaque black | `bg-black/80` |
| Default text | White | `text-white` |
| Goals | Red | `text-red-500` |
| Assists | Blue | `text-blue-500` |
| Points | White | `text-white` |
| +/- (positive) | Green | `text-green-500` |
| +/- (negative) | Red | `text-red-500` |
| Goalie accent | Cyan / teal | `text-cyan-400` |
| Team accent | Amber / gold | `text-amber-400` |
| Trigger accent | Purple / violet | `text-purple-400` |

### Typography

All text must be readable at 1920x1080 on a broadcast stream — viewers are watching at various resolutions and distances.

| Element | Size | Weight |
|---|---|---|
| Player / team name | 18px | Bold (700) |
| Stat values | 16px | Semibold (600) |
| Stat labels | 14px | Normal (400) |
| Secondary info (position, rank) | 13px | Normal (400) |

### Card Dimensions

| Property | Value |
|---|---|
| Width | 280px |
| Min height | 100px |
| Max height | 200px (soft — grows with content) |
| Padding | 16px |
| Border radius | 8px |
| Gap between stacked cards | 12px (`gap-3`) |

### OBS Constraints

- Root element: fully transparent (`bg-transparent`), no scrollbars, no body margin
- No rapidly flashing elements — animations use gentle easing
- No interactive elements visible in the overlay (buttons, inputs live on `/settings` route, not in the overlay)

---

## Animations

Defined in `index.css` (or a dedicated `animations.css`), shared by all card components.

### Entrance — slide in from left + fade

```css
@keyframes card-enter {
  from {
    opacity: 0;
    transform: translateX(-100px);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}
```

Duration: **0.3s**, easing: `ease-out`. Applied on mount.

### Exit — fade out

```css
@keyframes card-exit {
  to {
    opacity: 0;
  }
}
```

Duration: **0.2s**, easing: `ease-in`. Applied when the 8s dismiss timer fires, before unmounting.

All card components (StatCard, GoalieCard, TeamCard, and future TriggerCard) reuse these same keyframes.

---

## Component Specs

### `OverlayCanvas.tsx` — Card Queue Manager

**Responsibility:** receive payloads from the WebSocket, route each to the correct card component, manage the visible card queue.

**State:**
```typescript
type CardItem = {
  id: string            // e.g. "player_8478402_1743098400000"
  payload: StatPayload
}
```

**Behavior:**

1. Use `useOverlaySocket` to get incoming payloads
2. On new payload:
   - `type === "system"` — update an internal status flag, do NOT add a card
   - All other types — generate `id` from `${type}_${payload.id || payload.abbrev}_${payload.ts}`
   - **Dedup:** if same entity was received within the last 2 seconds, skip
   - Push to card queue
3. **Max 3 cards visible** — if the queue exceeds 3, remove the oldest
4. Route by `payload.type`:
   - `"player"` — `<StatCard>`
   - `"goalie"` — `<GoalieCard>`
   - `"team"` — `<TeamCard>`
   - `"trigger"` — `<TriggerCard>` (post-MVP, one line to add)
5. On card `onExpire` callback — remove card from state by `id`

**Layout:** bottom-left stack, newest card at the bottom.

```
┌──────────────────────────────────────────────────────────────┐
│                                                              │
│                         1920 x 1080                          │
│                      (transparent)                           │
│                                                              │
│                                                              │
│                                                              │
│                                                              │
│                                                              │
│  ┌─── oldest card ───┐                                       │
│  └───────────────────┘                                       │
│  ┌─── middle card ───┐                                       │
│  └───────────────────┘                                       │
│  ┌─── newest card ───┐                                       │
│  └───────────────────┘                                       │
│  ↑ bottom-8 left-8                                           │
└──────────────────────────────────────────────────────────────┘
```

Tailwind positioning: `absolute bottom-8 left-8 flex flex-col-reverse gap-3`

---

### `StatCard.tsx` — Skater Card

**Props:** `{ payload: PlayerPayload, onExpire: () => void }`

**Auto-dismiss:** `useEffect` sets `setTimeout(onExpire, 8000)` on mount, clears on unmount.

**Layout:**

```
┌──────────────────────────────────────┐
│  [●]  Connor McDavid          EDM   │  ← 40px circular avatar + name (bold) + team
│       C                              │  ← position (muted, small)
├──────────────────────────────────────┤
│  32 G    100 A    132 PTS            │  ← goals (red), assists (blue), points (white)
│  +15                                 │  ← plus/minus (green if +, red if -)
└──────────────────────────────────────┘
   [●] = 40px rounded-full headshot (initials fallback on error)
```

Stat values are large and colored. Labels ("G", "A", "PTS") are smaller and muted. The `display` string from the payload can be used as a fallback or tooltip, but the card renders from individual `stats` fields for color coding.

---

### `GoalieCard.tsx` — Goalie Card

**Props:** `{ payload: GoaliePayload, onExpire: () => void }`

Same animation and auto-dismiss behavior as StatCard.

**Layout:**

```
┌──────────────────────────────────────┐
│  [●]  Jacob Markstrom         NJD   │  ← 40px circular avatar + name (bold) + team
│       G                              │  ← position (cyan accent)
├──────────────────────────────────────┤
│  .907 SV%     2.98 GAA               │  ← save pct + GAA (cyan accent)
│  2 SO         22W 19L 4OT            │  ← shutouts + record (white)
└──────────────────────────────────────┘
   [●] = 40px rounded-full headshot (initials fallback on error)
   cyan-400 accent throughout
```

Save percentage formatted without leading zero (`.907` not `0.907`).

---

### `TeamCard.tsx` — Team Card

**Props:** `{ payload: TeamPayload, onExpire: () => void }`

Same animation and auto-dismiss behavior as StatCard.

**Layout:**

```
┌──────────────────────────────────────┐
│  [▣]  Edmonton Oilers                │  ← 48px rounded-lg logo + full team name
├──────────────────────────────────────┤
│  42W   20L   5OT     89 PTS          │  ← record + points (white)
│  Div: 2nd   Conf: 3rd                │  ← rankings (muted)
└──────────────────────────────────────┘
   [▣] = 48px rounded-lg logo (abbrev text fallback on error)
   amber-400 accent on fallback text
```

The header displays a team logo (48px `rounded-lg`) replacing the abbreviation; full team name beside it in white.

---

## Hook Specs

### `useOverlaySocket.ts`

**Interface:**
```typescript
function useOverlaySocket(url: string): {
  latestPayload: StatPayload | null
  systemEvent: SystemPayload | null
  isConnected: boolean
}
```

- Connects on mount to `ws://localhost:8000/ws`
- **Envelope unwrap:** every message is `{ v: 1, payload: ... }` — the hook strips the envelope and returns `payload`
- Discriminates on `payload.type` to separate system events from stat payloads
- **Auto-reconnect:** on close, reconnect with exponential backoff (1s, 2s, 4s, capped at 5s)
- The `StatPayload` union type already includes `TriggerPayload` — when triggers are implemented, no changes needed here

### `useMicCapture.ts`

**Interface:**
```typescript
function useMicCapture(audioWsUrl: string): {
  start: () => Promise<void>
  stop: () => void
  isRecording: boolean
  isConnected: boolean
}
```

- Calls `navigator.mediaDevices.getUserMedia({ audio: true })` on `start()`
- Opens a WebSocket to `ws://localhost:8000/audio`
- Uses `MediaRecorder` with a short `timeslice` (~250ms)

**Important:** the `timeslice` is purely a batching interval — it controls how often `ondataavailable` fires and we send bytes over the WebSocket. It has no effect on transcription. The backend pipes every blob straight to Deepgram as a continuous audio stream. Deepgram's streaming engine determines when an utterance is complete via its `is_final` flag. A shorter timeslice means Deepgram starts processing audio sooner (lower latency); a longer one just delays the first bytes.

- Handles mic permission denial gracefully (set `isRecording: false`, surface error)
- In OBS, mic access requires "Allow Audio Capture" enabled on the browser source

---

## Root Setup

### `main.tsx`

```tsx
<div className="w-screen h-screen bg-transparent overflow-hidden relative">
  <OverlayCanvas />
</div>
```

Only `OverlayCanvas` is mounted. No router, no navigation — the overlay is a single full-screen view.

### `index.html`

- `<body>` background set to transparent
- Title: "NHL Radio Overlay"
- No favicon needed (not visible in OBS)

---

## Future-Proofing

The MVP architecture is designed so that each planned post-MVP feature slots in with minimal changes — no rewrites or structural refactors.

### Custom Triggers

**Components:** `TriggerCard.tsx`, `TriggerBuilder.tsx`, `TriggerList.tsx`, `useTriggers.ts`

**What changes:**
- Add `case "trigger"` to the type switch in `OverlayCanvas` (one line)
- `TriggerCard` follows the exact same pattern as the other cards: accepts `TriggerPayload` + `onExpire`, reuses shared animations, 8s auto-dismiss. Its accent color is purple/violet. It renders a dynamic `fields` array (label/value pairs) since trigger payloads vary.
- `TriggerBuilder` and `TriggerList` are admin/config UI. They live on a separate `/settings` route, completely outside the overlay canvas. They use `useTriggers.ts` (a REST hook for CRUD on `/triggers`) — no overlap with `useOverlaySocket`.

**What doesn't change:** `useOverlaySocket` (the `StatPayload` union already includes `TriggerPayload`), `OverlayCanvas` structure, existing card components, `useMicCapture`.

See [`docs/project/trigger-builder.md`](project/trigger-builder.md) for the full trigger system spec.

### Configurable Stat Fields

**What changes:**
- Stat cards switch from hardcoded rows to iterating a `fields` array in the payload. The backend applies the user's field config before broadcast, so the frontend just renders what it receives.
- Card height becomes variable (a 2-field card is shorter than a 6-field card). Use `min-h-[100px]` + auto-grow, capped at 4-5 rows for broadcast readability.
- A label map in the frontend translates field keys to display strings (e.g. `"toi_per_game"` to `"TOI/GP"`).
- A `FieldConfigPanel` component lives on `/settings` — toggle fields on/off, drag to reorder, preview a mock card.

**What doesn't change:** `OverlayCanvas` routing, hooks, animation system, card lifecycle.

See the "User-configurable stat fields" note in [`docs/notes.md`](notes.md).

### Action-Based Overlays

If the extractor adds an `actions` field to the payload (e.g. `"scoring"`, `"penalty"`, `"fight"`), cards can use it for conditional styling — highlight the relevant stat, change accent color, or show a contextual icon. No new component type needed; it's purely visual logic within existing cards.

See the "Keyword-based action extraction" note in [`docs/notes.md`](notes.md).

### LLM-Generated Card HTML

A post-MVP enhancement to triggers where each trigger gets a custom HTML template generated by an LLM at creation time. `TriggerCard` checks if a template exists for the trigger ID:
- **Template exists:** substitute `{{label}}` tokens with field values, sanitize (DOMPurify), render via `dangerouslySetInnerHTML`
- **No template:** fall back to the generic field-list layout

Entirely contained within `TriggerCard` — no other component is affected.

### StandingsPayload (Multi-Team Table)

A new payload type `"standings"` with an array of team entries. Would need a new `StandingsCard.tsx` component with a table layout and one new case in `OverlayCanvas` routing. Same lifecycle (enter animation, auto-dismiss, `onExpire`) as other cards.

See the "Future Consideration" section in [`docs/api/ws-payload-contract.md`](api/ws-payload-contract.md).

---

## OBS Integration

| Setting | Value |
|---|---|
| URL | `http://localhost:8000` |
| Resolution | 1920 x 1080 |
| Background | Transparent (check "Custom CSS" or OBS transparency option) |
| Audio capture | Enable "Allow Audio Capture" on the browser source |

The overlay is display-only once running — no user interaction in OBS. All configuration (mic start/stop, trigger management, field settings) happens on the `/settings` route opened in a regular browser, not through the OBS source.
