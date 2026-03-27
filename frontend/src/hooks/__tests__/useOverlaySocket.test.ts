import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { useOverlaySocket } from '../useOverlaySocket'
import type { Envelope } from '../../types/payloads'

// ---------------------------------------------------------------------------
// Minimal WebSocket mock
// Tracks all created instances so tests can control them.
// ---------------------------------------------------------------------------

class MockWebSocket {
  static instances: MockWebSocket[] = []

  url: string
  readyState = 0 // CONNECTING

  onopen: (() => void) | null = null
  onmessage: ((event: { data: string }) => void) | null = null
  onclose: (() => void) | null = null

  readonly closeSpy = vi.fn()

  constructor(url: string) {
    this.url = url
    MockWebSocket.instances.push(this)
  }

  close(): void {
    this.closeSpy()
    this.readyState = 3 // CLOSED
    this.onclose?.()
  }

  // ── test helpers ──────────────────────────────────────────────────────────

  /** Simulate the server accepting the connection. */
  open(): void {
    this.readyState = 1 // OPEN
    this.onopen?.()
  }

  /** Simulate a stat message arriving from the backend. */
  receive(envelope: Envelope): void {
    this.onmessage?.({ data: JSON.stringify(envelope) })
  }

  /** Simulate the connection dropping (e.g. network loss). Does NOT call closeSpy. */
  drop(): void {
    this.readyState = 3
    this.onclose?.()
  }
}

function latestWs(): MockWebSocket {
  return MockWebSocket.instances[MockWebSocket.instances.length - 1]
}

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

const playerEnvelope: Envelope = {
  v: 1,
  payload: {
    type: 'player',
    id: 8478402,
    name: 'Connor McDavid',
    team: 'EDM',
    position: 'C',
    headshot_url: 'https://example.com/mcdavid.png',
    stats: { season: '20242025', games_played: 62, goals: 32, assists: 100, points: 132, plus_minus: 15 },
    display: 'McDavid · 32G 100A 132PTS +15',
    ts: 1743098400000,
  },
}

const systemEnvelope: Envelope = {
  v: 1,
  payload: {
    type: 'system',
    event: 'transcriber_ready',
    message: 'Deepgram connected',
    ts: 1743098400000,
  },
}

// ---------------------------------------------------------------------------
// Suite
// ---------------------------------------------------------------------------

beforeEach(() => {
  MockWebSocket.instances = []
  vi.stubGlobal('WebSocket', MockWebSocket)
  vi.useFakeTimers()
})

afterEach(() => {
  vi.unstubAllGlobals()
  vi.useRealTimers()
})

describe('useOverlaySocket — initial state', () => {
  it('starts disconnected', () => {
    const { result } = renderHook(() => useOverlaySocket('ws://test'))
    expect(result.current.isConnected).toBe(false)
  })

  it('starts with no payload', () => {
    const { result } = renderHook(() => useOverlaySocket('ws://test'))
    expect(result.current.latestPayload).toBeNull()
  })

  it('starts with no system event', () => {
    const { result } = renderHook(() => useOverlaySocket('ws://test'))
    expect(result.current.systemEvent).toBeNull()
  })
})

describe('useOverlaySocket — connection lifecycle', () => {
  it('connects to the provided URL on mount', () => {
    renderHook(() => useOverlaySocket('ws://localhost:8000/ws'))
    expect(latestWs().url).toBe('ws://localhost:8000/ws')
  })

  it('sets isConnected true when the socket opens', () => {
    const { result } = renderHook(() => useOverlaySocket('ws://test'))
    act(() => { latestWs().open() })
    expect(result.current.isConnected).toBe(true)
  })

  it('sets isConnected false when the socket closes', () => {
    const { result } = renderHook(() => useOverlaySocket('ws://test'))
    act(() => { latestWs().open() })
    act(() => { latestWs().drop() })
    expect(result.current.isConnected).toBe(false)
  })
})

describe('useOverlaySocket — message handling', () => {
  it('puts a player payload in latestPayload', () => {
    const { result } = renderHook(() => useOverlaySocket('ws://test'))
    act(() => { latestWs().open() })
    act(() => { latestWs().receive(playerEnvelope) })
    expect(result.current.latestPayload).toEqual(playerEnvelope.payload)
  })

  it('routes system events to systemEvent, not latestPayload', () => {
    const { result } = renderHook(() => useOverlaySocket('ws://test'))
    act(() => { latestWs().open() })
    act(() => { latestWs().receive(systemEnvelope) })
    expect(result.current.systemEvent).toEqual(systemEnvelope.payload)
    expect(result.current.latestPayload).toBeNull()
  })

  it('does not crash on malformed JSON', () => {
    renderHook(() => useOverlaySocket('ws://test'))
    act(() => { latestWs().open() })
    expect(() => {
      act(() => { latestWs().onmessage?.({ data: 'not json at all' }) })
    }).not.toThrow()
  })
})

describe('useOverlaySocket — reconnect backoff', () => {
  it('reconnects after 1s on first disconnect', () => {
    renderHook(() => useOverlaySocket('ws://test'))
    act(() => { latestWs().open() })
    act(() => { latestWs().drop() })

    expect(MockWebSocket.instances).toHaveLength(1)
    act(() => { vi.advanceTimersByTime(1000) })
    expect(MockWebSocket.instances).toHaveLength(2)
  })

  it('reconnects after 2s on second disconnect', () => {
    renderHook(() => useOverlaySocket('ws://test'))
    act(() => { latestWs().open() })
    act(() => { latestWs().drop() })
    act(() => { vi.advanceTimersByTime(1000) }) // 1st reconnect

    act(() => { latestWs().drop() }) // 2nd disconnect
    act(() => { vi.advanceTimersByTime(1999) })
    expect(MockWebSocket.instances).toHaveLength(2) // not yet

    act(() => { vi.advanceTimersByTime(1) })
    expect(MockWebSocket.instances).toHaveLength(3)
  })

  it('caps backoff at 5s after many disconnects', () => {
    renderHook(() => useOverlaySocket('ws://test'))

    // burn through backoff sequence: 1s, 2s, 4s, 5s, 5s
    for (let i = 0; i < 5; i++) {
      act(() => { latestWs().drop() })
      act(() => { vi.advanceTimersByTime(5000) }) // always enough for any step
    }

    // All 6 sockets created (1 initial + 5 reconnects)
    expect(MockWebSocket.instances).toHaveLength(6)
  })

  it('resets retry count after a successful connection', () => {
    renderHook(() => useOverlaySocket('ws://test'))
    act(() => { latestWs().open() })
    act(() => { latestWs().drop() })
    act(() => { vi.advanceTimersByTime(1000) }) // reconnect

    // Connection succeeds again — retry counter resets
    act(() => { latestWs().open() })
    act(() => { latestWs().drop() })

    // Should be back to 1s delay
    act(() => { vi.advanceTimersByTime(999) })
    expect(MockWebSocket.instances).toHaveLength(2) // not yet

    act(() => { vi.advanceTimersByTime(1) })
    expect(MockWebSocket.instances).toHaveLength(3)
  })
})

describe('useOverlaySocket — cleanup on unmount', () => {
  it('closes the WebSocket on unmount', () => {
    const { unmount } = renderHook(() => useOverlaySocket('ws://test'))
    act(() => { latestWs().open() })
    const ws = latestWs()

    unmount()

    expect(ws.closeSpy).toHaveBeenCalledOnce()
  })

  it('does not reconnect after unmount', () => {
    const { unmount } = renderHook(() => useOverlaySocket('ws://test'))
    act(() => { latestWs().open() })
    unmount()

    act(() => { vi.advanceTimersByTime(10_000) })

    expect(MockWebSocket.instances).toHaveLength(1) // no new connections
  })
})
