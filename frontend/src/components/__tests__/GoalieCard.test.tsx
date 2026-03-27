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

  it('renders shutouts value', () => {
    render(<GoalieCard payload={payload} onExpire={() => {}} />)
    expect(screen.getByText('2')).toBeTruthy()
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
