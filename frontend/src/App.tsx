import { useHashLocation } from 'wouter/use-hash-location'
import { Router, Route } from 'wouter'
import { SettingsProvider } from './contexts/SettingsContext'
import { LandingPage } from './pages/LandingPage'
import { OverlayPage } from './pages/OverlayPage'
import { SettingsPage } from './pages/SettingsPage'
import { useMicCapture } from './hooks/useMicCapture'
import { WS_AUDIO_URL } from './config'

function AppRoutes() {
  const { start, stop, isRecording, isConnected } = useMicCapture(WS_AUDIO_URL)

  return (
    <Router hook={useHashLocation}>
      <Route path="/">
        {() => <LandingPage start={start} stop={stop} isRecording={isRecording} isConnected={isConnected} />}
      </Route>
      <Route path="/overlay" component={OverlayPage} />
      <Route path="/settings" component={SettingsPage} />
    </Router>
  )
}

export default function App() {
  return (
    <SettingsProvider>
      <AppRoutes />
    </SettingsProvider>
  )
}
