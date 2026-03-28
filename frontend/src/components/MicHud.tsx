type MicHudProps = {
  start: () => Promise<void>
  stop: () => void
  isRecording: boolean
  isConnected: boolean
}

export function MicHud({ start, stop, isRecording, isConnected }: MicHudProps) {
  return (
    <div className="absolute top-4 right-4 flex items-center gap-2 bg-black/60 backdrop-blur-sm rounded-full px-3 py-1.5 select-none">
      <span
        className={`w-2 h-2 rounded-full flex-shrink-0 ${isConnected ? 'bg-green-400' : 'bg-red-500'}`}
        title={isConnected ? 'Connected to backend' : 'Disconnected'}
      />
      <button
        onClick={isRecording ? stop : start}
        className={`text-xs font-semibold px-2 py-0.5 rounded-full border-0 cursor-pointer transition-colors ${
          isRecording
            ? 'text-red-400 hover:text-red-300'
            : 'text-green-400 hover:text-green-300'
        } bg-transparent`}
      >
        {isRecording ? 'Stop' : 'Start'}
      </button>
      <span className="text-xs text-gray-400">
        {isRecording ? 'Recording…' : 'Idle'}
      </span>
    </div>
  )
}
