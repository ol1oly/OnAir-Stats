import { memo } from 'react'
import { OverlayCanvas } from '../components/OverlayCanvas'

const MemoCanvas = memo(OverlayCanvas)

export function OverlayPage() {
  return (
    <div className="w-screen h-screen bg-transparent overflow-hidden relative">
      <MemoCanvas />
    </div>
  )
}
