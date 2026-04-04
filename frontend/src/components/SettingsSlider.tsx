import React from 'react'

type Stop<T> = { label: string; value: T }

type Props<T> = {
  label: string
  description: string
  stops: Stop<T>[]
  value: T
  onChange: (value: T) => void
}

export function SettingsSlider<T>({ label, description, stops, value, onChange }: Props<T>) {
  const currentIndex = stops.findIndex(s => s.value === value)
  const safeIndex = currentIndex === -1 ? 0 : currentIndex

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const idx = parseInt(e.target.value, 10)
    onChange(stops[idx].value)
  }

  return (
    <div className="flex flex-col gap-1">
      <div className="flex items-baseline justify-between">
        <span className="text-white font-semibold text-sm">{label}</span>
        <span className="text-blue-400 text-sm font-medium">{stops[safeIndex].label}</span>
      </div>
      <input
        type="range"
        min={0}
        max={stops.length - 1}
        step={1}
        value={safeIndex}
        onChange={handleChange}
        className="w-full accent-blue-500 cursor-pointer"
      />
      <span className="text-gray-400 text-xs">{description}</span>
    </div>
  )
}
