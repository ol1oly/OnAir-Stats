import { useState, useEffect } from 'react'
import { Link } from 'wouter'
import { useSettings, DEFAULTS } from '../contexts/SettingsContext'
import { SettingsSlider } from '../components/SettingsSlider'
import { CARD_DISPLAY_MS, MAX_CARDS } from '../config'

const MODEL_STOPS = [
    { label: 'Nova-2', value: 'nova-2' as const },
    { label: 'Nova-3', value: 'nova-3' as const },
]

const LANGUAGE_STOPS = [
    { label: 'English', value: 'en' as const },
    { label: 'French', value: 'fr' as const },
]

const SENSITIVITY_STOPS = [
    { label: 'Strict', value: { ngram: 90, partial: 96 } },
    { label: 'Balanced', value: { ngram: DEFAULTS.fuzzyNgramThreshold, partial: DEFAULTS.fuzzyPartialThreshold } },
    { label: 'Relaxed', value: { ngram: 72, partial: 82 } },
    { label: 'Open', value: { ngram: 62, partial: 74 } },
]

const CACHE_TTL_STOPS = [
    { label: '15 s', value: 15 },
    { label: '45 s', value: DEFAULTS.cacheTtl },
    { label: '2 min', value: 120 },
    { label: '5 min', value: 300 },
]

const CARD_DISPLAY_STOPS = [
    { label: '5 s', value: 5000 },
    { label: '8 s', value: CARD_DISPLAY_MS },
    { label: '12 s', value: 12000 },
    { label: '20 s', value: 20000 },
]

const MAX_CARDS_STOPS = [
    { label: '1', value: 1 },
    { label: '3', value: MAX_CARDS },
    { label: '5', value: 5 },
]

export function SettingsPage() {
    const { settings, updateSetting, updateSettings, applySettings, hasUnappliedChanges } = useSettings()
    const [justApplied, setJustApplied] = useState(false)

    useEffect(() => {
        if (!justApplied) return
        const id = setTimeout(() => setJustApplied(false), 2000)
        return () => clearTimeout(id)
    }, [justApplied])

    // Sensitivity uses two backend params; map the current ngram threshold to a stop.
    // SENSITIVITY_STOPS is module-level so object identity is stable — findIndex works with ===.
    const currentSensitivityValue = SENSITIVITY_STOPS.find(
        s => s.value.ngram === settings.fuzzyNgramThreshold
    )?.value ?? SENSITIVITY_STOPS[1].value

    const handleSensitivityChange = (v: { ngram: number; partial: number }) => {
        updateSettings({ fuzzyNgramThreshold: v.ngram, fuzzyPartialThreshold: v.partial })
    }

    const handleBackButton = (e: React.MouseEvent<HTMLAnchorElement>) => {
        if (hasUnappliedChanges && !window.confirm("you have unapplied changes. Do you still want to change page?")) {
            e.preventDefault();
        }
    }

    const handleApply = async () => {
        await applySettings()
        setJustApplied(true)
    }

    return (
        <div className="w-screen h-screen bg-gray-950 text-white flex flex-col">
            <header className="flex items-center gap-4 px-6 py-4 border-b border-gray-800 shrink-0">
                <Link onClick={handleBackButton} href="/" className="text-gray-400 hover:text-white transition-colors text-sm">
                    ← Back
                </Link>
                <h1 className="text-xl font-bold">Settings</h1>
            </header>

            <main className="flex-1 overflow-y-auto scrollbar-none px-6 py-8">
                <div className="max-w-xl mx-auto flex flex-col gap-8">
                    <section className="flex flex-col gap-6">
                        <h2 className="text-xs font-semibold uppercase tracking-widest text-gray-500">Backend</h2>

                        <SettingsSlider
                            label="Deepgram Model"
                            description="Speech-to-text model for live transcription. Nova-2 is recommended."
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
                    </section>

                    <section className="flex flex-col gap-6">
                        <h2 className="text-xs font-semibold uppercase tracking-widest text-gray-500">Frontend</h2>

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
                    </section>
                </div>
            </main>

            <footer className="shrink-0 border-t border-gray-800 px-6 py-4">
                <div className="max-w-xl mx-auto flex items-center gap-4">
                    <button
                        disabled={!hasUnappliedChanges}
                        onClick={handleApply}
                        className={`px-5 py-2 rounded-lg text-sm font-semibold transition-colors ${hasUnappliedChanges
                            ? 'bg-blue-600 hover:bg-blue-500 text-white'
                            : 'bg-gray-700 text-gray-400 cursor-default'
                            }`}
                    >
                        {justApplied ? '✓ Applied' : 'Apply'}
                    </button>
                    {hasUnappliedChanges && !justApplied && (
                        <span className="text-xs text-yellow-400">Unsaved backend changes</span>
                    )}
                </div>
            </footer>
        </div>
    )
}
