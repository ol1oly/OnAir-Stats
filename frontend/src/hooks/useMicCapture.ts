import { useCallback, useRef, useState } from 'react'

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

  const start = useCallback(async () => {
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

      recorder.start(250) // ~250ms batching interval — Deepgram determines transcript boundaries via is_final
      setIsRecording(true)
    }

    ws.onclose = () => {
      setIsConnected(false)
      setIsRecording(false)
    }

    ws.onerror = () => {
      setIsConnected(false)
    }
  }, [audioWsUrl])

  const stop = useCallback(() => {
    recorderRef.current?.stop()
    recorderRef.current = null

    streamRef.current?.getTracks().forEach((t) => t.stop())
    streamRef.current = null

    wsRef.current?.close()
    wsRef.current = null

    setIsRecording(false)
    setIsConnected(false)
  }, [])

  return { start, stop, isRecording, isConnected }
}
