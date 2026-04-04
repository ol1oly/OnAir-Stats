import { createContext, useContext, useState, useEffect, useCallback, type ReactNode } from 'react'

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

const DEFAULTS: Settings = {
  model: 'nova-2',
  language: 'en',
  fuzzyNgramThreshold: 82,
  fuzzyPartialThreshold: 90,
  cacheTtl: 45,
  cardDisplayMs: 8000,
  maxCards: 3,
}

const VALID_MODELS = new Set<Settings['model']>(['nova-2', 'nova-3'])

function loadFromStorage(): Settings {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return DEFAULTS
    const parsed = JSON.parse(raw) as Partial<Settings>
    const merged = { ...DEFAULTS, ...parsed }
    if (!VALID_MODELS.has(merged.model)) merged.model = DEFAULTS.model
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
}

const SettingsContext = createContext<SettingsContextValue | null>(null)

export function SettingsProvider({ children }: { children: ReactNode }) {
  const [settings, setSettings] = useState<Settings>(loadFromStorage)

  useEffect(() => {
    void postBackendSettings(settings)
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const updateSetting = useCallback(<K extends keyof Settings>(key: K, value: Settings[K]) => {
    setSettings(prev => {
      const next = { ...prev, [key]: value }
      saveToStorage(next)
      if (BACKEND_KEYS.has(key)) {
        void postBackendSettings(next)
      }
      return next
    })
  }, [])

  return (
    <SettingsContext.Provider value={{ settings, updateSetting }}>
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
