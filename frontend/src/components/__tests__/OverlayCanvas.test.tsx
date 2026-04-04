import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, act, fireEvent } from '@testing-library/react'
import React from 'react'
import { CARD_DISPLAY_MS, CARD_EXIT_MS, DEDUP_MS } from '../../config'
import { OverlayCanvas } from '../OverlayCanvas'
import { SettingsProvider } from '../../contexts/SettingsContext'
import type { PlayerPayload, GoaliePayload, TeamPayload } from '../../types/payloads'

vi.stubGlobal('fetch', vi.fn(() =>
  Promise.resolve({ ok: true, json: () => Promise.resolve({ ok: true }) } as Response)
))

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

function renderCanvas() {
  return render(
    React.createElement(SettingsProvider, null, React.createElement(OverlayCanvas))
  )
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
    const { rerender } = renderCanvas()
    act(() => {
      mockLatestPayload = player
      rerender(React.createElement(SettingsProvider, null, React.createElement(OverlayCanvas)))
    })
    expect(screen.getByText('Connor McDavid')).toBeTruthy()
  })

  it('renders GoalieCard for goalie payload', () => {
    const { rerender } = renderCanvas()
    act(() => {
      mockLatestPayload = goalie
      rerender(React.createElement(SettingsProvider, null, React.createElement(OverlayCanvas)))
    })
    expect(screen.getByText('Jacob Markstrom')).toBeTruthy()
  })

  it('renders TeamCard for team payload', () => {
    const { rerender } = renderCanvas()
    act(() => {
      mockLatestPayload = team
      rerender(React.createElement(SettingsProvider, null, React.createElement(OverlayCanvas)))
    })
    expect(screen.getByText('Edmonton Oilers')).toBeTruthy()
  })
})

describe('OverlayCanvas — deduplication', () => {
  it('resets existing card instead of adding a duplicate when entity is still visible', () => {
    const { rerender } = renderCanvas()
    act(() => { mockLatestPayload = player; rerender(React.createElement(SettingsProvider, null, React.createElement(OverlayCanvas))) })
    act(() => { vi.advanceTimersByTime(1000) })
    act(() => {
      mockLatestPayload = { ...player, ts: player.ts + 1000 }
      rerender(React.createElement(SettingsProvider, null, React.createElement(OverlayCanvas)))
    })
    expect(screen.getAllByText('Connor McDavid')).toHaveLength(1)
  })

  it('adds a new card after prior card expires and dedup window passes', () => {
    const { rerender } = renderCanvas()
    act(() => { mockLatestPayload = player; rerender(React.createElement(SettingsProvider, null, React.createElement(OverlayCanvas))) })
    // card expires at CARD_DISPLAY_MS + CARD_EXIT_MS, dedup window (DEDUP_MS) ends after that
    const reappearDelay = CARD_DISPLAY_MS + CARD_EXIT_MS + DEDUP_MS + 1
    act(() => { vi.advanceTimersByTime(reappearDelay) })
    act(() => {
      mockLatestPayload = { ...player, ts: player.ts + reappearDelay }
      rerender(React.createElement(SettingsProvider, null, React.createElement(OverlayCanvas)))
    })
    expect(screen.getByText('Connor McDavid')).toBeTruthy()
  })

  it('does not add a duplicate card within the 2s dedup window when no active card', () => {
    const { rerender } = renderCanvas()
    act(() => { mockLatestPayload = player; rerender(React.createElement(SettingsProvider, null, React.createElement(OverlayCanvas))) })
    act(() => { vi.advanceTimersByTime(100) })
    act(() => {
      mockLatestPayload = { ...player, ts: player.ts + 100 }
      rerender(React.createElement(SettingsProvider, null, React.createElement(OverlayCanvas)))
    })
    expect(screen.getAllByText('Connor McDavid')).toHaveLength(1)
  })
})

describe('OverlayCanvas — max cards', () => {
  it('shows at most 3 cards, dropping the oldest', () => {
    const { rerender } = renderCanvas()
    const p1: PlayerPayload = { ...player, id: 10, name: 'Player One', ts: 1000 }
    const p2: PlayerPayload = { ...player, id: 11, name: 'Player Two', ts: 2000 }
    const p3: PlayerPayload = { ...player, id: 12, name: 'Player Three', ts: 3000 }
    const p4: PlayerPayload = { ...player, id: 13, name: 'Player Four', ts: 4000 }

    act(() => { mockLatestPayload = p1; rerender(React.createElement(SettingsProvider, null, React.createElement(OverlayCanvas))) })
    act(() => { mockLatestPayload = p2; rerender(React.createElement(SettingsProvider, null, React.createElement(OverlayCanvas))) })
    act(() => { mockLatestPayload = p3; rerender(React.createElement(SettingsProvider, null, React.createElement(OverlayCanvas))) })
    act(() => { mockLatestPayload = p4; rerender(React.createElement(SettingsProvider, null, React.createElement(OverlayCanvas))) })

    expect(screen.queryByText('Player One')).toBeNull()
    expect(screen.getByText('Player Two')).toBeTruthy()
    expect(screen.getByText('Player Three')).toBeTruthy()
    expect(screen.getByText('Player Four')).toBeTruthy()
  })
})

describe('OverlayCanvas — timer', () => {
  it(`removes card after ${CARD_DISPLAY_MS + CARD_EXIT_MS}ms`, () => {
    const { rerender } = renderCanvas()
    act(() => { mockLatestPayload = player; rerender(React.createElement(SettingsProvider, null, React.createElement(OverlayCanvas))) })
    expect(screen.getByText('Connor McDavid')).toBeTruthy()
    act(() => { vi.advanceTimersByTime(CARD_DISPLAY_MS + CARD_EXIT_MS + 1) })
    expect(screen.queryByText('Connor McDavid')).toBeNull()
  })

  it('click on card resets its 8s timer', () => {
    const { rerender } = renderCanvas()
    act(() => { mockLatestPayload = player; rerender(React.createElement(SettingsProvider, null, React.createElement(OverlayCanvas))) })
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
