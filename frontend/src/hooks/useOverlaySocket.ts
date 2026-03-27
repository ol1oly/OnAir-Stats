import { useCallback, useEffect, useRef, useState } from 'react'
import type { Envelope, StatPayload, SystemPayload } from '../types/payloads'

// Backoff delays in ms: 1s, 2s, 4s, then cap at 5s
const BACKOFF_MS = [1000, 2000, 4000, 5000]

export function useOverlaySocket(url: string): {
  latestPayload: StatPayload | null
  systemEvent: SystemPayload | null
  isConnected: boolean
} {
  const [latestPayload, setLatestPayload] = useState<StatPayload | null>(null)
  const [systemEvent, setSystemEvent] = useState<SystemPayload | null>(null)
  const [isConnected, setIsConnected] = useState(false)

  const wsRef = useRef<WebSocket | null>(null)
  const retryRef = useRef(0)
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const activeRef = useRef(true) // set to false on unmount to suppress reconnects
  const urlRef = useRef(url)
  urlRef.current = url

  const connect = useCallback(() => {
    if (!activeRef.current) return

    const ws = new WebSocket(urlRef.current)
    wsRef.current = ws

    ws.onopen = () => {
      retryRef.current = 0
      setIsConnected(true)
    }

    ws.onmessage = (event: MessageEvent<string>) => {
      try {
        const { payload } = JSON.parse(event.data) as Envelope
        if (payload.type === 'system') {
          setSystemEvent(payload as SystemPayload)
        } else {
          setLatestPayload(payload)
        }
      } catch {
        // malformed message — ignore
      }
    }

    ws.onclose = () => {
      setIsConnected(false)
      if (!activeRef.current) return
      const delay = BACKOFF_MS[Math.min(retryRef.current, BACKOFF_MS.length - 1)]
      retryRef.current++
      timerRef.current = setTimeout(connect, delay)
    }
  }, []) // stable reference — reads url from urlRef

  useEffect(() => {
    activeRef.current = true
    connect()
    return () => {
      activeRef.current = false
      if (timerRef.current !== null) clearTimeout(timerRef.current)
      wsRef.current?.close()
    }
  }, [connect])

  return { latestPayload, systemEvent, isConnected }
}
