import { useMicCapture } from './hooks/useMicCapture'

const AUDIO_WS_URL = 'ws://localhost:8000/audio'

export default function App() {
  const { start, stop, isRecording, isConnected } = useMicCapture(AUDIO_WS_URL)

  return (
    <div style={{ padding: 24, display: 'flex', alignItems: 'center', gap: 12 }}>
      <button
        onClick={isRecording ? stop : start}
        style={{
          padding: '8px 20px',
          borderRadius: 6,
          border: 'none',
          cursor: 'pointer',
          fontWeight: 600,
          fontSize: 14,
          color: '#fff',
          background: isRecording ? '#dc2626' : '#16a34a',
        }}
      >
        {isRecording ? 'Stop' : 'Start'}
      </button>

      <span
        style={{
          width: 10,
          height: 10,
          borderRadius: '50%',
          background: isConnected ? '#22c55e' : '#ef4444',
          display: 'inline-block',
        }}
        title={isConnected ? 'Connected to backend' : 'Disconnected'}
      />

      <span style={{ fontSize: 13, color: '#6b7280' }}>
        {isRecording ? 'Recording…' : 'Idle'}
      </span>
    </div>
  )
}
