import { Link } from 'wouter'
import { WS_AUDIO_URL } from '../config'
import { useMicCapture } from '../hooks/useMicCapture'

export function LandingPage() {
  const { start, stop, isRecording, isConnected } = useMicCapture(WS_AUDIO_URL)

  return (
    <div className="w-screen h-screen bg-gray-950 flex flex-col items-center justify-center gap-8 text-white select-none">
      <div className="flex flex-col items-center gap-2">
        <h1 className="text-4xl font-bold tracking-tight">NHL Radio Overlay</h1>
        <p className="text-gray-400 text-sm">Real-time stat cards from live commentary</p>
      </div>

      <div className="flex items-center gap-3">
        <span
          className={`w-3 h-3 rounded-full flex-shrink-0 ${isConnected ? 'bg-green-400' : 'bg-red-500'}`}
          title={isConnected ? 'Connected to backend' : 'Disconnected'}
        />
        <span className="text-sm text-gray-300">
          {isConnected ? 'Connected' : 'Not connected'}
        </span>
      </div>

      <button
        onClick={isRecording ? stop : start}
        className={`px-8 py-3 rounded-full text-base font-semibold transition-colors cursor-pointer border-0 ${
          isRecording
            ? 'bg-red-600 hover:bg-red-500 text-white'
            : 'bg-green-600 hover:bg-green-500 text-white'
        }`}
      >
        {isRecording ? 'Stop Recording' : 'Start Recording'}
      </button>

      <div className="flex gap-6 text-sm">
        <Link href="/overlay" className="text-blue-400 hover:text-blue-300 underline-offset-2 hover:underline transition-colors">
          Open Overlay
        </Link>
        <Link href="/settings" className="text-blue-400 hover:text-blue-300 underline-offset-2 hover:underline transition-colors">
          Settings
        </Link>
      </div>
    </div>
  )
}
