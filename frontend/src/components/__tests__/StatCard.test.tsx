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
    render(<StatCard payload={payload} isExiting={false} />)
    expect(screen.getByText('Connor McDavid')).toBeTruthy()
  })

  it('renders the team abbreviation', () => {
    render(<StatCard payload={payload} isExiting={false} />)
    expect(screen.getByText('EDM')).toBeTruthy()
  })

  it('renders goals value', () => {
    render(<StatCard payload={payload} isExiting={false} />)
    expect(screen.getByText('32')).toBeTruthy()
  })

  it('renders positive plus_minus with + prefix', () => {
    render(<StatCard payload={payload} isExiting={false} />)
    expect(screen.getByText('+15')).toBeTruthy()
  })

  it('renders negative plus_minus without extra sign', () => {
    const neg = { ...payload, stats: { ...payload.stats, plus_minus: -5 } }
    render(<StatCard payload={neg} isExiting={false} />)
    expect(screen.getByText('-5')).toBeTruthy()
  })
})

describe('StatCard — headshot', () => {
  it('renders img with headshot_url as src', () => {
    const { container } = render(<StatCard payload={payload} isExiting={false} />)
    const img = container.querySelector('img')
    expect(img?.getAttribute('src')).toBe('https://example.com/mcdavid.png')
  })

  it('shows initials fallback (CM) when image errors', () => {
    const { container } = render(<StatCard payload={payload} isExiting={false} />)
    fireEvent.error(container.querySelector('img')!)
    expect(container.querySelector('img')).toBeNull()
    expect(screen.getByText('CM')).toBeTruthy()
  })
})

describe('StatCard — animation', () => {
  it('applies card-enter class when not exiting', () => {
    const { container } = render(<StatCard payload={payload} isExiting={false} />)
    expect(container.firstChild).toHaveProperty('className')
    expect((container.firstChild as HTMLElement).className).toContain('card-enter')
  })

  it('applies card-exit class when exiting', () => {
    const { container } = render(<StatCard payload={payload} isExiting={true} />)
    expect((container.firstChild as HTMLElement).className).toContain('card-exit')
  })
})
