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
