import { Link } from 'wouter'
import { useSettings } from '../contexts/SettingsContext'
import { SettingsSlider } from '../components/SettingsSlider'

const MODEL_STOPS = [
  { label: 'Nova', value: 'nova' as const },
  { label: 'Nova-2', value: 'nova-2' as const },
  { label: 'Whisper Large', value: 'whisper-large' as const },
]

const LANGUAGE_STOPS = [
  { label: 'English', value: 'en' as const },
  { label: 'French', value: 'fr' as const },
]

const SENSITIVITY_STOPS = [
  { label: 'Strict', value: { ngram: 90, partial: 96 } },
  { label: 'Balanced', value: { ngram: 82, partial: 90 } },
  { label: 'Relaxed', value: { ngram: 72, partial: 82 } },
  { label: 'Open', value: { ngram: 62, partial: 74 } },
]

const CACHE_TTL_STOPS = [
  { label: '15 s', value: 15 },
  { label: '45 s', value: 45 },
  { label: '2 min', value: 120 },
  { label: '5 min', value: 300 },
]

const CARD_DISPLAY_STOPS = [
  { label: '5 s', value: 5000 },
  { label: '8 s', value: 8000 },
  { label: '12 s', value: 12000 },
  { label: '20 s', value: 20000 },
]

const MAX_CARDS_STOPS = [
  { label: '1', value: 1 },
  { label: '3', value: 3 },
  { label: '5', value: 5 },
]

export function SettingsPage() {
  const { settings, updateSetting } = useSettings()

  // Sensitivity uses two backend params; map the current ngram threshold to a stop.
  // SENSITIVITY_STOPS is module-level so object identity is stable — findIndex works with ===.
  const currentSensitivityValue = SENSITIVITY_STOPS.find(
    s => s.value.ngram === settings.fuzzyNgramThreshold
  )?.value ?? SENSITIVITY_STOPS[1].value

  const handleSensitivityChange = (v: { ngram: number; partial: number }) => {
    updateSetting('fuzzyNgramThreshold', v.ngram)
    updateSetting('fuzzyPartialThreshold', v.partial)
  }

  return (
    <div className="w-screen min-h-screen bg-gray-950 text-white flex flex-col">
      <header className="flex items-center gap-4 px-6 py-4 border-b border-gray-800">
        <Link href="/" className="text-gray-400 hover:text-white transition-colors text-sm">
          ← Back
        </Link>
        <h1 className="text-xl font-bold">Settings</h1>
      </header>

      <main className="flex-1 px-6 py-8 max-w-xl mx-auto w-full flex flex-col gap-8">
        <SettingsSlider
          label="Deepgram Model"
          description="Speech-to-text model. Nova-2 is fast and accurate. Whisper-large is slower but more precise."
          stops={MODEL_STOPS}
          value={settings.model}
          onChange={v => updateSetting('model', v)}
        />

        <SettingsSlider
          label="Broadcast Language"
          description="Language of the audio commentary. Changing this restarts the transcriber (~1-2s)."
          stops={LANGUAGE_STOPS}
          value={settings.language}
          onChange={v => updateSetting('language', v)}
        />

        <SettingsSlider
          label="Name Matching Sensitivity"
          description="How strictly player and team names must match the transcript. Lower = more matches, more false positives."
          stops={SENSITIVITY_STOPS}
          value={currentSensitivityValue}
          onChange={handleSensitivityChange}
        />

        <SettingsSlider
          label="Stats Cache TTL"
          description="How long player and team stats are cached before re-fetching from the NHL API."
          stops={CACHE_TTL_STOPS}
          value={settings.cacheTtl}
          onChange={v => updateSetting('cacheTtl', v)}
        />

        <SettingsSlider
          label="Card Display Duration"
          description="How long each stat card stays on screen before sliding out."
          stops={CARD_DISPLAY_STOPS}
          value={settings.cardDisplayMs}
          onChange={v => updateSetting('cardDisplayMs', v)}
        />

        <SettingsSlider
          label="Max Visible Cards"
          description="Maximum number of stat cards visible at once. Oldest card is dropped when the limit is exceeded."
          stops={MAX_CARDS_STOPS}
          value={settings.maxCards}
          onChange={v => updateSetting('maxCards', v)}
        />
      </main>
    </div>
  )
}
