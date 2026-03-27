# Card Images Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add player headshots to StatCard/GoalieCard and team logos to TeamCard; create all three card components and the OverlayCanvas that routes them.

**Architecture:** Card components are new files under `frontend/src/components/`. Each card receives a typed payload prop and an `onExpire` callback. Images load from URLs already present in the payloads; a React state flag swaps in an initials/abbreviation fallback on error. OverlayCanvas consumes `useOverlaySocket`, manages a deduped queue of up to 3 cards, and routes each payload type to the right component.

**Tech Stack:** React 19, TypeScript, Tailwind CSS v4, Vitest, @testing-library/react, jsdom

---

## File Map

| Action | File | Responsibility |
|---|---|---|
| Modify | `frontend/src/index.css` | Replace Vite scaffold styles with overlay base + card animation keyframes |
| Create | `frontend/src/components/StatCard.tsx` | Skater stat card with circular headshot avatar |
| Create | `frontend/src/components/__tests__/StatCard.test.tsx` | StatCard unit tests |
| Create | `frontend/src/components/GoalieCard.tsx` | Goalie stat card with circular headshot avatar |
| Create | `frontend/src/components/__tests__/GoalieCard.test.tsx` | GoalieCard unit tests |
| Create | `frontend/src/components/TeamCard.tsx` | Team card: logo replaces abbreviation |
| Create | `frontend/src/components/__tests__/TeamCard.test.tsx` | TeamCard unit tests |
| Create | `frontend/src/components/OverlayCanvas.tsx` | Card queue manager; routes payloads to correct card |
| Create | `frontend/src/components/__tests__/OverlayCanvas.test.tsx` | OverlayCanvas routing + dedup tests |
| Modify | `frontend/src/main.tsx` | Mount OverlayCanvas in transparent full-screen root |
| Modify | `docs/frontend-design.md` | Update layout ASCII diagrams for all three cards |
| Modify | `docs/project/task.md` | Mark OPT-04 done; update CARD/TEAM/GOALIE/OVL tasks |

---

## Task 1: Replace index.css with overlay base styles + card animations

**Files:**
- Modify: `frontend/src/index.css`

The existing `index.css` has Vite scaffold styles (`#root` centered column, typography) that will conflict with the full-screen overlay. Replace it entirely.

- [ ] **Step 1.1: Replace index.css**

```css
/* frontend/src/index.css */
@import "tailwindcss";

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

@keyframes card-exit {
  to {
    opacity: 0;
  }
}

.card-enter {
  animation: card-enter 0.3s ease-out;
}

.card-exit {
  animation: card-exit 0.2s ease-in forwards;
}

body {
  margin: 0;
  background: transparent;
}

#root {
  width: 100vw;
  height: 100vh;
  overflow: hidden;
  position: relative;
}
```

- [ ] **Step 1.2: Run the dev server to verify it starts without errors**

```bash
cd frontend && npm run dev
```

Expected: dev server starts at `http://localhost:5173`, no console errors.

- [ ] **Step 1.3: Commit**

```bash
git add frontend/src/index.css
git commit -m "style: replace Vite scaffold CSS with overlay base styles and card animations"
```

---

## Task 2: StatCard — skater card with circular headshot

**Files:**
- Create: `frontend/src/components/StatCard.tsx`
- Create: `frontend/src/components/__tests__/StatCard.test.tsx`

**Layout:**
```
┌────────────────────────────────────┐
│  [●] Connor McDavid          EDM   │  ← 40px circle + name (bold) + team (muted)
│      C                             │  ← position (muted, small)
├────────────────────────────────────┤
│  32 G    100 A    132 PTS          │  ← goals (red), assists (blue), points (white)
│  +15                               │  ← plus/minus (green if +, red if -)
└────────────────────────────────────┘
```

- [ ] **Step 2.1: Create the test file**

```tsx
// frontend/src/components/__tests__/StatCard.test.tsx
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { StatCard } from '../StatCard'
import type { PlayerPayload } from '../../types/payloads'

const payload: PlayerPayload = {
  type: 'player',
  id: 8478402,
  name: 'Connor McDavid',
  team: 'EDM',
  position: 'C',
  headshot_url: 'https://example.com/mcdavid.png',
  stats: {
    season: '20242025',
    games_played: 62,
    goals: 32,
    assists: 100,
    points: 132,
    plus_minus: 15,
  },
  display: 'McDavid · 32G 100A 132PTS +15',
  ts: 1743098400000,
}

beforeEach(() => { vi.useFakeTimers() })
afterEach(() => { vi.useRealTimers() })

describe('StatCard — content', () => {
  it('renders the player name', () => {
    render(<StatCard payload={payload} onExpire={() => {}} />)
    expect(screen.getByText('Connor McDavid')).toBeTruthy()
  })

  it('renders the team abbreviation', () => {
    render(<StatCard payload={payload} onExpire={() => {}} />)
    expect(screen.getByText('EDM')).toBeTruthy()
  })

  it('renders goals value', () => {
    render(<StatCard payload={payload} onExpire={() => {}} />)
    expect(screen.getByText('32')).toBeTruthy()
  })

  it('renders positive plus_minus with + prefix', () => {
    render(<StatCard payload={payload} onExpire={() => {}} />)
    expect(screen.getByText('+15')).toBeTruthy()
  })

  it('renders negative plus_minus without extra sign', () => {
    const neg = { ...payload, stats: { ...payload.stats, plus_minus: -5 } }
    render(<StatCard payload={neg} onExpire={() => {}} />)
    expect(screen.getByText('-5')).toBeTruthy()
  })
})

describe('StatCard — headshot', () => {
  it('renders img with headshot_url as src', () => {
    const { container } = render(<StatCard payload={payload} onExpire={() => {}} />)
    const img = container.querySelector('img')
    expect(img?.getAttribute('src')).toBe('https://example.com/mcdavid.png')
  })

  it('shows initials fallback (CM) when image errors', () => {
    const { container } = render(<StatCard payload={payload} onExpire={() => {}} />)
    fireEvent.error(container.querySelector('img')!)
    expect(container.querySelector('img')).toBeNull()
    expect(screen.getByText('CM')).toBeTruthy()
  })
})

describe('StatCard — lifecycle', () => {
  it('calls onExpire after 8200ms', () => {
    const onExpire = vi.fn()
    render(<StatCard payload={payload} onExpire={onExpire} />)
    vi.advanceTimersByTime(8000)
    expect(onExpire).not.toHaveBeenCalled()
    vi.advanceTimersByTime(200)
    expect(onExpire).toHaveBeenCalledOnce()
  })
})
```

- [ ] **Step 2.2: Run tests — verify they fail**

```bash
cd frontend && npm test
```

Expected: FAIL — `Cannot find module '../StatCard'`

- [ ] **Step 2.3: Create the component**

```tsx
// frontend/src/components/StatCard.tsx
import { useEffect, useState } from 'react'
import type { PlayerPayload } from '../types/payloads'

function initials(name: string): string {
  const parts = name.trim().split(' ')
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase()
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase()
}

type Props = { payload: PlayerPayload; onExpire: () => void }

export function StatCard({ payload, onExpire }: Props) {
  const [imgError, setImgError] = useState(false)
  const [isExiting, setIsExiting] = useState(false)

  useEffect(() => {
    const t = setTimeout(() => {
      setIsExiting(true)
      setTimeout(onExpire, 200)
    }, 8000)
    return () => clearTimeout(t)
  }, [onExpire])

  const pm = payload.stats.plus_minus
  const pmStr = pm >= 0 ? `+${pm}` : `${pm}`
  const pmClass = pm >= 0 ? 'text-green-500' : 'text-red-500'

  return (
    <div className={`w-[280px] bg-black/80 rounded-lg p-4 ${isExiting ? 'card-exit' : 'card-enter'}`}>
      <div className="flex items-center gap-2.5">
        {imgError ? (
          <div className="w-10 h-10 rounded-full bg-gray-700 flex items-center justify-center text-white text-xs font-bold flex-shrink-0">
            {initials(payload.name)}
          </div>
        ) : (
          <img
            src={payload.headshot_url}
            alt={payload.name}
            className="w-10 h-10 rounded-full object-cover flex-shrink-0"
            onError={() => setImgError(true)}
          />
        )}
        <div className="flex-1 min-w-0">
          <div className="flex items-baseline justify-between">
            <span className="text-white font-bold text-[18px] truncate">{payload.name}</span>
            <span className="text-gray-400 text-[13px] ml-2 flex-shrink-0">{payload.team}</span>
          </div>
          <div className="text-gray-400 text-[13px]">{payload.position}</div>
        </div>
      </div>
      <div className="border-t border-gray-700 mt-3 pt-3">
        <div className="flex gap-4">
          <span>
            <span className="text-red-500 font-semibold text-[16px]">{payload.stats.goals}</span>
            <span className="text-gray-400 text-[13px] ml-1">G</span>
          </span>
          <span>
            <span className="text-blue-500 font-semibold text-[16px]">{payload.stats.assists}</span>
            <span className="text-gray-400 text-[13px] ml-1">A</span>
          </span>
          <span>
            <span className="text-white font-semibold text-[16px]">{payload.stats.points}</span>
            <span className="text-gray-400 text-[13px] ml-1">PTS</span>
          </span>
        </div>
        <div className={`${pmClass} text-[14px] font-semibold mt-1`}>{pmStr}</div>
      </div>
    </div>
  )
}
```

- [ ] **Step 2.4: Run tests — verify they pass**

```bash
cd frontend && npm test
```

Expected: all StatCard tests PASS.

- [ ] **Step 2.5: Commit**

```bash
git add frontend/src/components/StatCard.tsx frontend/src/components/__tests__/StatCard.test.tsx
git commit -m "feat: add StatCard with circular player headshot"
```

---

## Task 3: GoalieCard — goalie card with circular headshot

**Files:**
- Create: `frontend/src/components/GoalieCard.tsx`
- Create: `frontend/src/components/__tests__/GoalieCard.test.tsx`

**Layout:**
```
┌────────────────────────────────────┐
│  [●] Jacob Markstrom         NJD   │  ← 40px circle + name (bold) + team (muted)
│      G                             │  ← position in cyan
├────────────────────────────────────┤
│  .907 SV%    2.98 GAA              │  ← cyan accent
│  2 SO        22W 19L 4OT           │  ← white
└────────────────────────────────────┘
```

- [ ] **Step 3.1: Create the test file**

```tsx
// frontend/src/components/__tests__/GoalieCard.test.tsx
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { GoalieCard } from '../GoalieCard'
import type { GoaliePayload } from '../../types/payloads'

const payload: GoaliePayload = {
  type: 'goalie',
  id: 8474593,
  name: 'Jacob Markstrom',
  team: 'NJD',
  headshot_url: 'https://example.com/markstrom.png',
  stats: {
    season: '20242025',
    games_played: 48,
    wins: 22,
    losses: 19,
    ot_losses: 4,
    save_percentage: 0.907,
    goals_against_avg: 2.98,
    shutouts: 2,
  },
  display: 'Markstrom · .907 SV% 2.98 GAA 2 SO',
  ts: 1743098400000,
}

beforeEach(() => { vi.useFakeTimers() })
afterEach(() => { vi.useRealTimers() })

describe('GoalieCard — content', () => {
  it('renders the goalie name', () => {
    render(<GoalieCard payload={payload} onExpire={() => {}} />)
    expect(screen.getByText('Jacob Markstrom')).toBeTruthy()
  })

  it('renders the team abbreviation', () => {
    render(<GoalieCard payload={payload} onExpire={() => {}} />)
    expect(screen.getByText('NJD')).toBeTruthy()
  })

  it('renders save percentage without leading zero', () => {
    render(<GoalieCard payload={payload} onExpire={() => {}} />)
    expect(screen.getByText('.907')).toBeTruthy()
  })

  it('renders GAA formatted to 2 decimal places', () => {
    render(<GoalieCard payload={payload} onExpire={() => {}} />)
    expect(screen.getByText('2.98')).toBeTruthy()
  })

  it('renders W-L-OT record', () => {
    render(<GoalieCard payload={payload} onExpire={() => {}} />)
    expect(screen.getByText('22W 19L 4OT')).toBeTruthy()
  })
})

describe('GoalieCard — headshot', () => {
  it('renders img with headshot_url as src', () => {
    const { container } = render(<GoalieCard payload={payload} onExpire={() => {}} />)
    const img = container.querySelector('img')
    expect(img?.getAttribute('src')).toBe('https://example.com/markstrom.png')
  })

  it('shows initials fallback (JM) when image errors', () => {
    const { container } = render(<GoalieCard payload={payload} onExpire={() => {}} />)
    fireEvent.error(container.querySelector('img')!)
    expect(container.querySelector('img')).toBeNull()
    expect(screen.getByText('JM')).toBeTruthy()
  })
})

describe('GoalieCard — lifecycle', () => {
  it('calls onExpire after 8200ms', () => {
    const onExpire = vi.fn()
    render(<GoalieCard payload={payload} onExpire={onExpire} />)
    vi.advanceTimersByTime(8000)
    expect(onExpire).not.toHaveBeenCalled()
    vi.advanceTimersByTime(200)
    expect(onExpire).toHaveBeenCalledOnce()
  })
})
```

- [ ] **Step 3.2: Run tests — verify they fail**

```bash
cd frontend && npm test
```

Expected: FAIL — `Cannot find module '../GoalieCard'`

- [ ] **Step 3.3: Create the component**

```tsx
// frontend/src/components/GoalieCard.tsx
import { useEffect, useState } from 'react'
import type { GoaliePayload } from '../types/payloads'

function initials(name: string): string {
  const parts = name.trim().split(' ')
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase()
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase()
}

type Props = { payload: GoaliePayload; onExpire: () => void }

export function GoalieCard({ payload, onExpire }: Props) {
  const [imgError, setImgError] = useState(false)
  const [isExiting, setIsExiting] = useState(false)

  useEffect(() => {
    const t = setTimeout(() => {
      setIsExiting(true)
      setTimeout(onExpire, 200)
    }, 8000)
    return () => clearTimeout(t)
  }, [onExpire])

  const svPct = payload.stats.save_percentage.toFixed(3).replace('0.', '.')
  const gaa = payload.stats.goals_against_avg.toFixed(2)
  const { wins, losses, ot_losses, shutouts } = payload.stats

  return (
    <div className={`w-[280px] bg-black/80 rounded-lg p-4 ${isExiting ? 'card-exit' : 'card-enter'}`}>
      <div className="flex items-center gap-2.5">
        {imgError ? (
          <div className="w-10 h-10 rounded-full bg-gray-700 flex items-center justify-center text-white text-xs font-bold flex-shrink-0">
            {initials(payload.name)}
          </div>
        ) : (
          <img
            src={payload.headshot_url}
            alt={payload.name}
            className="w-10 h-10 rounded-full object-cover flex-shrink-0"
            onError={() => setImgError(true)}
          />
        )}
        <div className="flex-1 min-w-0">
          <div className="flex items-baseline justify-between">
            <span className="text-white font-bold text-[18px] truncate">{payload.name}</span>
            <span className="text-gray-400 text-[13px] ml-2 flex-shrink-0">{payload.team}</span>
          </div>
          <div className="text-cyan-400 text-[13px]">G</div>
        </div>
      </div>
      <div className="border-t border-gray-700 mt-3 pt-3">
        <div className="flex gap-4">
          <span>
            <span className="text-cyan-400 font-semibold text-[16px]">{svPct}</span>
            <span className="text-gray-400 text-[13px] ml-1">SV%</span>
          </span>
          <span>
            <span className="text-cyan-400 font-semibold text-[16px]">{gaa}</span>
            <span className="text-gray-400 text-[13px] ml-1">GAA</span>
          </span>
          <span>
            <span className="text-white font-semibold text-[16px]">{shutouts}</span>
            <span className="text-gray-400 text-[13px] ml-1">SO</span>
          </span>
        </div>
        <div className="text-white text-[14px] mt-1">{wins}W {losses}L {ot_losses}OT</div>
      </div>
    </div>
  )
}
```

- [ ] **Step 3.4: Run tests — verify they pass**

```bash
cd frontend && npm test
```

Expected: all GoalieCard tests PASS.

- [ ] **Step 3.5: Commit**

```bash
git add frontend/src/components/GoalieCard.tsx frontend/src/components/__tests__/GoalieCard.test.tsx
git commit -m "feat: add GoalieCard with circular player headshot"
```

---

## Task 4: TeamCard — team logo replaces abbreviation

**Files:**
- Create: `frontend/src/components/TeamCard.tsx`
- Create: `frontend/src/components/__tests__/TeamCard.test.tsx`

**Layout:**
```
┌────────────────────────────────────┐
│  [■] Edmonton Oilers               │  ← 48px rounded logo + full team name (bold)
│      Div: 2nd · Conf: 3rd          │  ← rankings (muted)
├────────────────────────────────────┤
│  42W   20L   5OT     89 PTS        │  ← record (white) + points (amber)
└────────────────────────────────────┘
  abbreviation (EDM) not shown — logo is the identifier
```

- [ ] **Step 4.1: Create the test file**

```tsx
// frontend/src/components/__tests__/TeamCard.test.tsx
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { TeamCard } from '../TeamCard'
import type { TeamPayload } from '../../types/payloads'

const payload: TeamPayload = {
  type: 'team',
  name: 'Edmonton Oilers',
  abbrev: 'EDM',
  logo_url: 'https://example.com/edm.svg',
  stats: {
    season: '20242025',
    wins: 42,
    losses: 20,
    ot_losses: 5,
    points: 89,
    games_played: 67,
    goals_for: 244,
    goals_against: 201,
    point_pct: 0.664,
  },
  conference_rank: 3,
  division_rank: 2,
  display: 'EDM · 42W 20L 5OT 89PTS',
  ts: 1743098400000,
}

beforeEach(() => { vi.useFakeTimers() })
afterEach(() => { vi.useRealTimers() })

describe('TeamCard — content', () => {
  it('renders the full team name', () => {
    render(<TeamCard payload={payload} onExpire={() => {}} />)
    expect(screen.getByText('Edmonton Oilers')).toBeTruthy()
  })

  it('does NOT render the abbreviation as standalone text in the header', () => {
    render(<TeamCard payload={payload} onExpire={() => {}} />)
    // "EDM" should not appear as a header element — logo replaces it
    expect(screen.queryByText('EDM')).toBeNull()
  })

  it('renders division and conference ranks', () => {
    render(<TeamCard payload={payload} onExpire={() => {}} />)
    expect(screen.getByText('Div: 2nd · Conf: 3rd')).toBeTruthy()
  })

  it('renders win-loss-OT record', () => {
    render(<TeamCard payload={payload} onExpire={() => {}} />)
    expect(screen.getByText('42W')).toBeTruthy()
    expect(screen.getByText('20L')).toBeTruthy()
    expect(screen.getByText('5OT')).toBeTruthy()
  })

  it('renders points', () => {
    render(<TeamCard payload={payload} onExpire={() => {}} />)
    expect(screen.getByText('89 PTS')).toBeTruthy()
  })
})

describe('TeamCard — logo', () => {
  it('renders img with logo_url as src', () => {
    const { container } = render(<TeamCard payload={payload} onExpire={() => {}} />)
    const img = container.querySelector('img')
    expect(img?.getAttribute('src')).toBe('https://example.com/edm.svg')
  })

  it('shows abbreviation fallback (EDM) in amber when image errors', () => {
    const { container } = render(<TeamCard payload={payload} onExpire={() => {}} />)
    fireEvent.error(container.querySelector('img')!)
    expect(container.querySelector('img')).toBeNull()
    expect(screen.getByText('EDM')).toBeTruthy()
  })
})

describe('TeamCard — lifecycle', () => {
  it('calls onExpire after 8200ms', () => {
    const onExpire = vi.fn()
    render(<TeamCard payload={payload} onExpire={onExpire} />)
    vi.advanceTimersByTime(8000)
    expect(onExpire).not.toHaveBeenCalled()
    vi.advanceTimersByTime(200)
    expect(onExpire).toHaveBeenCalledOnce()
  })
})
```

- [ ] **Step 4.2: Run tests — verify they fail**

```bash
cd frontend && npm test
```

Expected: FAIL — `Cannot find module '../TeamCard'`

- [ ] **Step 4.3: Create the component**

```tsx
// frontend/src/components/TeamCard.tsx
import { useEffect, useState } from 'react'
import type { TeamPayload } from '../types/payloads'

function ordinal(n: number): string {
  if (n === 1) return 'st'
  if (n === 2) return 'nd'
  if (n === 3) return 'rd'
  return 'th'
}

type Props = { payload: TeamPayload; onExpire: () => void }

export function TeamCard({ payload, onExpire }: Props) {
  const [imgError, setImgError] = useState(false)
  const [isExiting, setIsExiting] = useState(false)

  useEffect(() => {
    const t = setTimeout(() => {
      setIsExiting(true)
      setTimeout(onExpire, 200)
    }, 8000)
    return () => clearTimeout(t)
  }, [onExpire])

  const divRank = `${payload.division_rank}${ordinal(payload.division_rank)}`
  const confRank = `${payload.conference_rank}${ordinal(payload.conference_rank)}`

  return (
    <div className={`w-[280px] bg-black/80 rounded-lg p-4 ${isExiting ? 'card-exit' : 'card-enter'}`}>
      <div className="flex items-center gap-3">
        {imgError ? (
          <div className="w-12 h-12 rounded-lg bg-gray-700 flex items-center justify-center text-amber-400 text-sm font-bold flex-shrink-0">
            {payload.abbrev}
          </div>
        ) : (
          <img
            src={payload.logo_url}
            alt={payload.name}
            className="w-12 h-12 rounded-lg object-contain flex-shrink-0"
            onError={() => setImgError(true)}
          />
        )}
        <div className="flex-1 min-w-0">
          <div className="text-white font-bold text-[18px] truncate">{payload.name}</div>
          <div className="text-gray-400 text-[13px]">Div: {divRank} · Conf: {confRank}</div>
        </div>
      </div>
      <div className="border-t border-gray-700 mt-3 pt-3">
        <div className="flex gap-4">
          <span className="text-white font-semibold text-[16px]">{payload.stats.wins}W</span>
          <span className="text-white font-semibold text-[16px]">{payload.stats.losses}L</span>
          <span className="text-white font-semibold text-[16px]">{payload.stats.ot_losses}OT</span>
          <span className="text-amber-400 font-semibold text-[16px]">{payload.stats.points} PTS</span>
        </div>
      </div>
    </div>
  )
}
```

- [ ] **Step 4.4: Run tests — verify they pass**

```bash
cd frontend && npm test
```

Expected: all TeamCard tests PASS.

- [ ] **Step 4.5: Commit**

```bash
git add frontend/src/components/TeamCard.tsx frontend/src/components/__tests__/TeamCard.test.tsx
git commit -m "feat: add TeamCard with team logo replacing abbreviation"
```

---

## Task 5: OverlayCanvas — card queue manager

**Files:**
- Create: `frontend/src/components/OverlayCanvas.tsx`
- Create: `frontend/src/components/__tests__/OverlayCanvas.test.tsx`

Routes incoming payloads to the correct card component. Deduplicates the same entity within a 2s window. Keeps at most 3 cards visible.

- [ ] **Step 5.1: Create the test file**

```tsx
// frontend/src/components/__tests__/OverlayCanvas.test.tsx
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, act } from '@testing-library/react'
import { OverlayCanvas } from '../OverlayCanvas'
import type { PlayerPayload, GoaliePayload, TeamPayload } from '../../types/payloads'

// ── mock useOverlaySocket ────────────────────────────────────────────────────
let mockLatestPayload: PlayerPayload | GoaliePayload | TeamPayload | null = null

vi.mock('../../hooks/useOverlaySocket', () => ({
  useOverlaySocket: () => ({ latestPayload: mockLatestPayload, systemEvent: null, isConnected: false }),
}))

// ── fixtures ─────────────────────────────────────────────────────────────────
const player: PlayerPayload = {
  type: 'player', id: 1, name: 'Connor McDavid', team: 'EDM', position: 'C',
  headshot_url: '', stats: { season: '20242025', games_played: 60, goals: 30, assists: 80, points: 110, plus_minus: 10 },
  display: '', ts: 1000,
}
const goalie: GoaliePayload = {
  type: 'goalie', id: 2, name: 'Jacob Markstrom', team: 'NJD', headshot_url: '',
  stats: { season: '20242025', games_played: 40, wins: 20, losses: 15, ot_losses: 3, save_percentage: 0.907, goals_against_avg: 2.80, shutouts: 2 },
  display: '', ts: 2000,
}
const team: TeamPayload = {
  type: 'team', name: 'Edmonton Oilers', abbrev: 'EDM', logo_url: '',
  stats: { season: '20242025', wins: 40, losses: 18, ot_losses: 4, points: 84, games_played: 62, goals_for: 220, goals_against: 180, point_pct: 0.677 },
  conference_rank: 2, division_rank: 1, display: '', ts: 3000,
}

beforeEach(() => {
  mockLatestPayload = null
  vi.useFakeTimers()
})
afterEach(() => {
  vi.useRealTimers()
})

describe('OverlayCanvas — routing', () => {
  it('renders StatCard for player payload', () => {
    const { rerender } = render(<OverlayCanvas />)
    act(() => {
      mockLatestPayload = player
      rerender(<OverlayCanvas />)
    })
    expect(screen.getByText('Connor McDavid')).toBeTruthy()
  })

  it('renders GoalieCard for goalie payload', () => {
    const { rerender } = render(<OverlayCanvas />)
    act(() => {
      mockLatestPayload = goalie
      rerender(<OverlayCanvas />)
    })
    expect(screen.getByText('Jacob Markstrom')).toBeTruthy()
  })

  it('renders TeamCard for team payload', () => {
    const { rerender } = render(<OverlayCanvas />)
    act(() => {
      mockLatestPayload = team
      rerender(<OverlayCanvas />)
    })
    expect(screen.getByText('Edmonton Oilers')).toBeTruthy()
  })
})

describe('OverlayCanvas — deduplication', () => {
  it('does not add a duplicate card for the same entity within 2s', () => {
    const { rerender } = render(<OverlayCanvas />)
    act(() => { mockLatestPayload = player; rerender(<OverlayCanvas />) })
    act(() => {
      mockLatestPayload = { ...player, ts: player.ts + 100 }
      rerender(<OverlayCanvas />)
    })
    expect(screen.getAllByText('Connor McDavid')).toHaveLength(1)
  })

  it('adds a card for the same entity after 2s', () => {
    const { rerender } = render(<OverlayCanvas />)
    act(() => { mockLatestPayload = player; rerender(<OverlayCanvas />) })
    act(() => { vi.advanceTimersByTime(2001) })
    act(() => {
      mockLatestPayload = { ...player, ts: player.ts + 2001 }
      rerender(<OverlayCanvas />)
    })
    expect(screen.getAllByText('Connor McDavid')).toHaveLength(2)
  })
})

describe('OverlayCanvas — max cards', () => {
  it('shows at most 3 cards, dropping the oldest', () => {
    const { rerender } = render(<OverlayCanvas />)
    const p1: PlayerPayload = { ...player, id: 10, name: 'Player One', ts: 1000 }
    const p2: PlayerPayload = { ...player, id: 11, name: 'Player Two', ts: 2000 }
    const p3: PlayerPayload = { ...player, id: 12, name: 'Player Three', ts: 3000 }
    const p4: PlayerPayload = { ...player, id: 13, name: 'Player Four', ts: 4000 }

    act(() => { mockLatestPayload = p1; rerender(<OverlayCanvas />) })
    act(() => { mockLatestPayload = p2; rerender(<OverlayCanvas />) })
    act(() => { mockLatestPayload = p3; rerender(<OverlayCanvas />) })
    act(() => { mockLatestPayload = p4; rerender(<OverlayCanvas />) })

    expect(screen.queryByText('Player One')).toBeNull()
    expect(screen.getByText('Player Two')).toBeTruthy()
    expect(screen.getByText('Player Three')).toBeTruthy()
    expect(screen.getByText('Player Four')).toBeTruthy()
  })
})
```

- [ ] **Step 5.2: Run tests — verify they fail**

```bash
cd frontend && npm test
```

Expected: FAIL — `Cannot find module '../OverlayCanvas'`

- [ ] **Step 5.3: Create the component**

```tsx
// frontend/src/components/OverlayCanvas.tsx
import { useCallback, useEffect, useRef, useState } from 'react'
import { useOverlaySocket } from '../hooks/useOverlaySocket'
import type { StatPayload } from '../types/payloads'
import { StatCard } from './StatCard'
import { GoalieCard } from './GoalieCard'
import { TeamCard } from './TeamCard'

const WS_URL = 'ws://localhost:8000/ws'
const MAX_CARDS = 3
const DEDUP_MS = 2000

type CardItem = { id: string; payload: StatPayload }

function entityKey(p: StatPayload): string {
  if (p.type === 'player' || p.type === 'goalie') return `${p.type}_${p.id}`
  if (p.type === 'team') return `team_${p.abbrev}`
  if (p.type === 'trigger') return `trigger_${p.id}`
  return 'system'
}

function cardId(p: StatPayload): string {
  if (p.type === 'player' || p.type === 'goalie') return `${p.type}_${p.id}_${p.ts}`
  if (p.type === 'team') return `team_${p.abbrev}_${p.ts}`
  if (p.type === 'trigger') return `trigger_${p.id}_${p.ts}`
  return `system_${p.ts}`
}

export function OverlayCanvas() {
  const { latestPayload } = useOverlaySocket(WS_URL)
  const [cards, setCards] = useState<CardItem[]>([])
  const seenRef = useRef<Map<string, number>>(new Map())

  const removeCard = useCallback((id: string) => {
    setCards(prev => prev.filter(c => c.id !== id))
  }, [])

  useEffect(() => {
    if (!latestPayload || latestPayload.type === 'system') return

    const key = entityKey(latestPayload)
    const now = Date.now()
    if (now - (seenRef.current.get(key) ?? 0) < DEDUP_MS) return
    seenRef.current.set(key, now)

    setCards(prev => {
      const next = [...prev, { id: cardId(latestPayload), payload: latestPayload }]
      return next.length > MAX_CARDS ? next.slice(next.length - MAX_CARDS) : next
    })
  }, [latestPayload])

  return (
    <div className="absolute bottom-8 left-8 flex flex-col-reverse gap-3">
      {cards.map(({ id, payload }) => {
        if (payload.type === 'player') return <StatCard key={id} payload={payload} onExpire={() => removeCard(id)} />
        if (payload.type === 'goalie') return <GoalieCard key={id} payload={payload} onExpire={() => removeCard(id)} />
        if (payload.type === 'team') return <TeamCard key={id} payload={payload} onExpire={() => removeCard(id)} />
        return null
      })}
    </div>
  )
}
```

- [ ] **Step 5.4: Run tests — verify all pass**

```bash
cd frontend && npm test
```

Expected: all OverlayCanvas tests PASS. Full suite PASS.

- [ ] **Step 5.5: Commit**

```bash
git add frontend/src/components/OverlayCanvas.tsx frontend/src/components/__tests__/OverlayCanvas.test.tsx
git commit -m "feat: add OverlayCanvas with card routing, dedup, and 3-card queue"
```

---

## Task 6: Wire main.tsx

**Files:**
- Modify: `frontend/src/main.tsx`

Replace the current `App`-mounted content with a full-screen transparent canvas that mounts `OverlayCanvas`.

- [ ] **Step 6.1: Update main.tsx**

```tsx
// frontend/src/main.tsx
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import { OverlayCanvas } from './components/OverlayCanvas'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <div className="w-screen h-screen bg-transparent overflow-hidden relative">
      <OverlayCanvas />
    </div>
  </StrictMode>,
)
```

- [ ] **Step 6.2: Run full test suite and build**

```bash
cd frontend && npm test && npm run build
```

Expected: all tests PASS, `dist/` generated with no TypeScript errors.

- [ ] **Step 6.3: Commit**

```bash
git add frontend/src/main.tsx
git commit -m "feat: mount OverlayCanvas as full-screen transparent root"
```

---

## Task 7: Update docs

**Files:**
- Modify: `docs/frontend-design.md`
- Modify: `docs/project/task.md`

- [ ] **Step 7.1: Update StatCard layout diagram in frontend-design.md**

Find the `StatCard.tsx — Skater Card` section and replace the layout block:

```
**Layout:**

```
┌────────────────────────────────────┐
│  [●] Connor McDavid          EDM   │  ← 40px circle headshot + name (bold) + team (muted)
│      C                             │  ← position (muted, small)
├────────────────────────────────────┤
│  32 G    100 A    132 PTS          │  ← goals (red), assists (blue), points (white)
│  +15                               │  ← plus/minus (green if +, red if -)
└────────────────────────────────────┘
   280px wide, bg-black/80, rounded-lg
   [●] = 40px rounded-full headshot; falls back to initials on error
```
```

- [ ] **Step 7.2: Update GoalieCard layout diagram in frontend-design.md**

Find the `GoalieCard.tsx — Goalie Card` section and replace the layout block:

```
**Layout:**

```
┌────────────────────────────────────┐
│  [●] Jacob Markstrom         NJD   │  ← 40px circle headshot + name (bold) + team (muted)
│      G                             │  ← position (cyan accent)
├────────────────────────────────────┤
│  .907 SV%     2.98 GAA             │  ← save pct + GAA (cyan accent)
│  2 SO         22W 19L 4OT          │  ← shutouts + record (white)
└────────────────────────────────────┘
   cyan-400 accent throughout
   [●] = 40px rounded-full headshot; falls back to initials on error
```
```

- [ ] **Step 7.3: Update TeamCard layout diagram in frontend-design.md**

Find the `TeamCard.tsx — Team Card` section and replace the layout block:

```
**Layout:**

```
┌────────────────────────────────────┐
│  [■] Edmonton Oilers               │  ← 48px rounded logo + full team name (bold, white)
│      Div: 2nd · Conf: 3rd          │  ← rankings (muted)
├────────────────────────────────────┤
│  42W   20L   5OT     89 PTS        │  ← record (white) + points (amber)
└────────────────────────────────────┘
   abbreviation (EDM) not shown — logo is the primary identifier
   [■] = 48px rounded-lg SVG logo (object-contain); falls back to abbrev in amber on error
```
```

- [ ] **Step 7.4: Update task.md — mark OPT-04 done and update card tasks**

In `docs/project/task.md`, find `OPT-04` and mark it completed:
```
- [x] **OPT-04** — Add team logo images to `TeamCard` — implemented: 48px rounded logo replaces abbreviation in header; fallback shows abbrev in amber on error
```

Mark these tasks completed (they are fully implemented by this plan):
- `CARD-01` through `CARD-05` — StatCard done
- `TEAM-01` through `TEAM-04` — TeamCard done
- `GOALIE-01` through `GOALIE-03` — GoalieCard done
- `OVL-01` through `OVL-05` — OverlayCanvas done
- `ROOT-01` through `ROOT-03` — main.tsx done

- [ ] **Step 7.5: Commit**

```bash
git add docs/frontend-design.md docs/project/task.md
git commit -m "docs: update card layout diagrams with headshots/logo; mark frontend tasks complete"
```

---

## Verification

After all tasks are complete:

```bash
# All tests pass
cd frontend && npm test

# Build succeeds
cd frontend && npm run build

# Backend serves the frontend
cd backend && backend/.venv/Scripts/python.exe -m uvicorn server:app --reload --port 8000
# Open http://localhost:8000 — transparent overlay canvas loads
# Open ws://localhost:8000/debug/inject (POST) to test a card appearing
```
