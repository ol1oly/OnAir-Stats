import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import { OverlayCanvas } from './components/OverlayCanvas'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <div className="w-screen h-screen bg-transparent overflow-hidden relative">
      <OverlayCanvas />
    </div>
  </StrictMode>,
)
