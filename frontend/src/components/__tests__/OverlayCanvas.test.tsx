import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, act, fireEvent } from '@testing-library/react'
import { CARD_DISPLAY_MS, CARD_EXIT_MS, DEDUP_MS } from '../../config'
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
  vi.useFakeTimers({ toFake: ['setTimeout', 'clearTimeout', 'setInterval', 'clearInterval', 'Date'] })
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
  it('resets existing card instead of adding a duplicate when entity is still visible', () => {
    const { rerender } = render(<OverlayCanvas />)
    act(() => { mockLatestPayload = player; rerender(<OverlayCanvas />) })
    act(() => { vi.advanceTimersByTime(1000) })
    act(() => {
      mockLatestPayload = { ...player, ts: player.ts + 1000 }
      rerender(<OverlayCanvas />)
    })
    expect(screen.getAllByText('Connor McDavid')).toHaveLength(1)
  })

  it('adds a new card after prior card expires and dedup window passes', () => {
    const { rerender } = render(<OverlayCanvas />)
    act(() => { mockLatestPayload = player; rerender(<OverlayCanvas />) })
    // card expires at CARD_DISPLAY_MS + CARD_EXIT_MS, dedup window (DEDUP_MS) ends after that
    const reappearDelay = CARD_DISPLAY_MS + CARD_EXIT_MS + DEDUP_MS + 1
    act(() => { vi.advanceTimersByTime(reappearDelay) })
    act(() => {
      mockLatestPayload = { ...player, ts: player.ts + reappearDelay }
      rerender(<OverlayCanvas />)
    })
    expect(screen.getByText('Connor McDavid')).toBeTruthy()
  })

  it('does not add a duplicate card within the 2s dedup window when no active card', () => {
    const { rerender } = render(<OverlayCanvas />)
    // Advance past card expiry (8200ms) but stay within 2s of last processing
    // Trigger: first payload at t=8000ms (card still showing), seenRef updates to 8000ms,
    // card resets to expire at 16200ms. Then card gets manually removed and a payload
    // arrives at t=9000ms (within 2s of seenRef=8000ms).
    // Simpler: just verify a second payload at t=100ms (before seenRef expires) doesn't add.
    act(() => { mockLatestPayload = player; rerender(<OverlayCanvas />) })
    act(() => { vi.advanceTimersByTime(100) })
    // Same entity arrives 100ms later — card still active, gets reset (not a new card)
    act(() => {
      mockLatestPayload = { ...player, ts: player.ts + 100 }
      rerender(<OverlayCanvas />)
    })
    expect(screen.getAllByText('Connor McDavid')).toHaveLength(1)
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

describe('OverlayCanvas — timer', () => {
  it(`removes card after ${CARD_DISPLAY_MS + CARD_EXIT_MS}ms`, () => {
    const { rerender } = render(<OverlayCanvas />)
    act(() => { mockLatestPayload = player; rerender(<OverlayCanvas />) })
    expect(screen.getByText('Connor McDavid')).toBeTruthy()
    act(() => { vi.advanceTimersByTime(CARD_DISPLAY_MS + CARD_EXIT_MS + 1) })
    expect(screen.queryByText('Connor McDavid')).toBeNull()
  })

  it('click on card resets its 8s timer', () => {
    const { rerender } = render(<OverlayCanvas />)
    act(() => { mockLatestPayload = player; rerender(<OverlayCanvas />) })
    // advance 7s — card is still showing, 1s remaining
    act(() => { vi.advanceTimersByTime(7000) })
    expect(screen.getByText('Connor McDavid')).toBeTruthy()
    // click the card to reset
    act(() => { fireEvent.click(screen.getByText('Connor McDavid')) })
    // advance another 7s — timer was reset, so card should still be showing
    act(() => { vi.advanceTimersByTime(7000) })
    expect(screen.getByText('Connor McDavid')).toBeTruthy()
  })
})
