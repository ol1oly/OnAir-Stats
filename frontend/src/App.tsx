import { memo } from 'react'
import { useMicCapture } from './hooks/useMicCapture'
import { OverlayCanvas } from './components/OverlayCanvas'
import { MicHud } from './components/MicHud'

const AUDIO_WS_URL = 'ws://localhost:8000/audio'
const MemoCanvas = memo(OverlayCanvas)

export default function App() {
  const { start, stop, isRecording, isConnected } = useMicCapture(AUDIO_WS_URL)
  return (
    <div className="w-screen h-screen bg-transparent overflow-hidden relative">
      <MemoCanvas />
      <MicHud start={start} stop={stop} isRecording={isRecording} isConnected={isConnected} />
    </div>
  )
}
