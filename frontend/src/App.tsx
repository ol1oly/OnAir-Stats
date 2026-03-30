import { memo } from 'react'
import { WS_AUDIO_URL } from './config'
import { useMicCapture } from './hooks/useMicCapture'
import { OverlayCanvas } from './components/OverlayCanvas'
import { MicHud } from './components/MicHud'
const MemoCanvas = memo(OverlayCanvas)

export default function App() {
  const { start, stop, isRecording, isConnected } = useMicCapture(WS_AUDIO_URL)
  return (
    <div className="w-screen h-screen bg-transparent overflow-hidden relative">
      <MemoCanvas />
      <MicHud start={start} stop={stop} isRecording={isRecording} isConnected={isConnected} />
    </div>
  )
}
