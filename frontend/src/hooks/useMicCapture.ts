import { useCallback, useEffect, useRef, useState } from 'react'
import { MIC_TIMESLICE_MS, AUDIO_WS_RECONNECT_DELAY_MS } from '../config'

export function useMicCapture(audioWsUrl: string): {
  start: () => Promise<void>
  stop: () => void
  isRecording: boolean
  isConnected: boolean
} {
  const [isRecording, setIsRecording] = useState(false)
  const [isConnected, setIsConnected] = useState(false)

  const wsRef = useRef<WebSocket | null>(null)
  const recorderRef = useRef<MediaRecorder | null>(null)
  const streamRef = useRef<MediaStream | null>(null)

  // true only when the user explicitly calls stop() — suppresses auto-reconnect
  const intentionalStopRef = useRef(false)
  // pending auto-reconnect timer
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  // stable ref to the latest start() so ws.onclose can schedule a reconnect
  const startRef = useRef<(() => Promise<void>) | undefined>(undefined)

  const start = useCallback(async () => {
    intentionalStopRef.current = false

    // cancel any pending reconnect (this call IS the reconnect)
    if (reconnectTimerRef.current !== null) {
      clearTimeout(reconnectTimerRef.current)
      reconnectTimerRef.current = null
    }

    // clean up any lingering resources from a previous session
    recorderRef.current?.stop()
    recorderRef.current = null
    streamRef.current?.getTracks().forEach((t) => t.stop())
    streamRef.current = null

    let stream: MediaStream
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    } catch (err) {
      console.error('[useMicCapture] Mic permission denied:', err)
      return
    }

    streamRef.current = stream

    const ws = new WebSocket(audioWsUrl)
    wsRef.current = ws

    ws.onopen = () => {
      setIsConnected(true)

      const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
        ? 'audio/webm;codecs=opus'
        : ''
      const recorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined)
      recorderRef.current = recorder

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0 && ws.readyState === WebSocket.OPEN) {
          ws.send(e.data)
        }
      }

      recorder.start(MIC_TIMESLICE_MS)
      setIsRecording(true)
    }

    ws.onclose = () => {
      // stop and release mic/recorder so the next start() gets a clean slate
      recorderRef.current?.stop()
      recorderRef.current = null
      streamRef.current?.getTracks().forEach((t) => t.stop())
      streamRef.current = null

      setIsConnected(false)
      setIsRecording(false)

      // auto-reconnect unless the user explicitly clicked Stop
      if (!intentionalStopRef.current) {
        reconnectTimerRef.current = setTimeout(() => {
          reconnectTimerRef.current = null
          startRef.current?.()
        }, AUDIO_WS_RECONNECT_DELAY_MS)
      }
    }

    ws.onerror = () => {
      setIsConnected(false)
      setIsRecording(false)
      // ws.onclose fires after onerror and handles reconnect
    }
  }, [audioWsUrl])

  // keep startRef pointing at the latest closure so ws.onclose can call it
  useEffect(() => {
    startRef.current = start
  }, [start])

  const stop = useCallback(() => {
    intentionalStopRef.current = true

    if (reconnectTimerRef.current !== null) {
      clearTimeout(reconnectTimerRef.current)
      reconnectTimerRef.current = null
    }

    recorderRef.current?.stop()
    recorderRef.current = null

    streamRef.current?.getTracks().forEach((t) => t.stop())
    streamRef.current = null

    wsRef.current?.close()
    wsRef.current = null

    setIsRecording(false)
    setIsConnected(false)
  }, [])

  useEffect(() => {
    return () => {
      if (reconnectTimerRef.current !== null) {
        clearTimeout(reconnectTimerRef.current)
      }
      recorderRef.current?.stop()
      recorderRef.current = null
      streamRef.current?.getTracks().forEach((t) => t.stop())
      streamRef.current = null
      wsRef.current?.close()
      wsRef.current = null
    }
  }, [])

  return { start, stop, isRecording, isConnected }
}
