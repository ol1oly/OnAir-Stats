import { createContext, useContext, useState, useEffect, useCallback, useRef, type ReactNode } from 'react'
import { CARD_DISPLAY_MS, MAX_CARDS } from '../config'

export interface Settings {
    model: 'nova-2' | 'nova-3'
    language: 'en' | 'fr'
    fuzzyNgramThreshold: number
    fuzzyPartialThreshold: number
    cacheTtl: number
    cardDisplayMs: number
    maxCards: number
}

const STORAGE_KEY = 'nhl_overlay_settings'

export const DEFAULTS: Settings = {
    model: 'nova-2',
    language: 'en',
    fuzzyNgramThreshold: 82,
    fuzzyPartialThreshold: 90, // in the future add a get endpoint to see what the actual values are here instead of hardcoding them here
    cacheTtl: 45,
    cardDisplayMs: CARD_DISPLAY_MS,
    maxCards: MAX_CARDS,
}

const VALID_MODELS = new Set<Settings['model']>(['nova-2', 'nova-3'])
const VALID_LANGUAGES = new Set<Settings['language']>(['en', 'fr'])

function loadFromStorage(): Settings {
    try {
        const raw = localStorage.getItem(STORAGE_KEY)
        if (!raw) return DEFAULTS
        const parsed = JSON.parse(raw) as Partial<Settings>
        const merged = { ...DEFAULTS, ...parsed }
        if (!VALID_MODELS.has(merged.model)) merged.model = DEFAULTS.model
        if (!VALID_LANGUAGES.has(merged.language)) merged.language = DEFAULTS.language
        return merged
    } catch {
        return DEFAULTS
    }
}

function saveToStorage(settings: Settings): void {
    try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(settings))
    } catch {
        // Storage write failures are silently ignored
    }
}

const BACKEND_KEYS = new Set<keyof Settings>([
    'model',
    'language',
    'fuzzyNgramThreshold',
    'fuzzyPartialThreshold',
    'cacheTtl',
])

function toBackendPayload(settings: Settings): Record<string, unknown> {
    return {
        model: settings.model,
        language: settings.language,
        fuzzy_ngram_threshold: settings.fuzzyNgramThreshold,
        fuzzy_partial_threshold: settings.fuzzyPartialThreshold,
        cache_ttl: settings.cacheTtl,
    }
}

async function postBackendSettings(settings: Settings): Promise<void> {
    try {
        await fetch('/settings', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(toBackendPayload(settings)),
        })
    } catch {
        // Network errors during settings sync are non-fatal
    }
}

interface SettingsContextValue {
    settings: Settings
    updateSetting: <K extends keyof Settings>(key: K, value: Settings[K]) => void
    updateSettings: (partial: Partial<Settings>) => void
    applySettings: () => Promise<void>
    hasUnappliedChanges: boolean
}

const SettingsContext = createContext<SettingsContextValue | null>(null)

export function SettingsProvider({ children }: { children: ReactNode }) {
    const [settings, setSettings] = useState<Settings>(loadFromStorage)
    const [hasUnappliedChanges, setHasUnappliedChanges] = useState(false)
    const settingsRef = useRef(settings)
    settingsRef.current = settings

    useEffect(() => {
        void postBackendSettings(settings)
    }, []) // eslint-disable-line react-hooks/exhaustive-deps

    const updateSetting = useCallback(<K extends keyof Settings>(key: K, value: Settings[K]) => {
        setSettings(prev => {
            const next = { ...prev, [key]: value }
            saveToStorage(next)
            return next
        })
        if (BACKEND_KEYS.has(key)) {
            setHasUnappliedChanges(true)
        }
    }, [])

    const updateSettings = useCallback((partial: Partial<Settings>) => {
        setSettings(prev => {
            const next = { ...prev, ...partial }
            saveToStorage(next)
            return next
        })
        const touchesBackend = Object.keys(partial).some(k => BACKEND_KEYS.has(k as keyof Settings))
        if (touchesBackend) setHasUnappliedChanges(true)
    }, [])

    const applySettings = useCallback(async () => {
        await postBackendSettings(settingsRef.current)
        setHasUnappliedChanges(false)
    }, [])

    return (
        <SettingsContext.Provider value={{ settings, updateSetting, updateSettings, applySettings, hasUnappliedChanges }}>
            {children}
        </SettingsContext.Provider>
    )
}

export function useSettings(): SettingsContextValue {
    const ctx = useContext(SettingsContext)
    if (ctx === null) {
        throw new Error('useSettings must be used inside <SettingsProvider>')
    }
    return ctx
}
