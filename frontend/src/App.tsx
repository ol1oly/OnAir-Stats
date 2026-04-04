import { useHashLocation } from 'wouter/use-hash-location'
import { Router, Route } from 'wouter'
import { SettingsProvider } from './contexts/SettingsContext'
import { LandingPage } from './pages/LandingPage'
import { OverlayPage } from './pages/OverlayPage'
import { SettingsPage } from './pages/SettingsPage'

export default function App() {
  return (
    <SettingsProvider>
      <Router hook={useHashLocation}>
        <Route path="/" component={LandingPage} />
        <Route path="/overlay" component={OverlayPage} />
        <Route path="/settings" component={SettingsPage} />
      </Router>
    </SettingsProvider>
  )
}
