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
  vi.useFakeTimers({ toFake: ['setTimeout', 'clearTimeout', 'Date'] })
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
