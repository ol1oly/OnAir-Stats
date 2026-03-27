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
