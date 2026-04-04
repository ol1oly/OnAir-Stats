import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import React from 'react'

const localStorageMock = (() => {
  let store: Record<string, string> = {}
  return {
    getItem: vi.fn((key: string) => store[key] ?? null),
    setItem: vi.fn((key: string, value: string) => { store[key] = value }),
    removeItem: vi.fn((key: string) => { delete store[key] }),
    clear: vi.fn(() => { store = {} }),
  }
})()

const fetchMock = vi.fn(() =>
  Promise.resolve({ ok: true, json: () => Promise.resolve({ ok: true }) } as Response)
)

beforeEach(() => {
  localStorageMock.clear()
  vi.stubGlobal('localStorage', localStorageMock)
  vi.stubGlobal('fetch', fetchMock)
  fetchMock.mockClear()
  localStorageMock.getItem.mockClear()
  localStorageMock.setItem.mockClear()
})

afterEach(() => {
  vi.unstubAllGlobals()
})

async function getHook() {
  const mod = await import('../../contexts/SettingsContext')
  return { useSettings: mod.useSettings, SettingsProvider: mod.SettingsProvider }
}

describe('useSettings — default values', () => {
  it('returns default model nova-2', async () => {
    const { useSettings, SettingsProvider } = await getHook()
    const wrapper = ({ children }: { children: React.ReactNode }) =>
      React.createElement(SettingsProvider, null, children)
    const { result } = renderHook(() => useSettings(), { wrapper })
    expect(result.current.settings.model).toBe('nova-2')
  })

  it('returns default language en', async () => {
    const { useSettings, SettingsProvider } = await getHook()
    const wrapper = ({ children }: { children: React.ReactNode }) =>
      React.createElement(SettingsProvider, null, children)
    const { result } = renderHook(() => useSettings(), { wrapper })
    expect(result.current.settings.language).toBe('en')
  })

  it('returns default fuzzyNgramThreshold 82', async () => {
    const { useSettings, SettingsProvider } = await getHook()
    const wrapper = ({ children }: { children: React.ReactNode }) =>
      React.createElement(SettingsProvider, null, children)
    const { result } = renderHook(() => useSettings(), { wrapper })
    expect(result.current.settings.fuzzyNgramThreshold).toBe(82)
  })

  it('returns default fuzzyPartialThreshold 90', async () => {
    const { useSettings, SettingsProvider } = await getHook()
    const wrapper = ({ children }: { children: React.ReactNode }) =>
      React.createElement(SettingsProvider, null, children)
    const { result } = renderHook(() => useSettings(), { wrapper })
    expect(result.current.settings.fuzzyPartialThreshold).toBe(90)
  })

  it('returns default cacheTtl 45', async () => {
    const { useSettings, SettingsProvider } = await getHook()
    const wrapper = ({ children }: { children: React.ReactNode }) =>
      React.createElement(SettingsProvider, null, children)
    const { result } = renderHook(() => useSettings(), { wrapper })
    expect(result.current.settings.cacheTtl).toBe(45)
  })

  it('returns default cardDisplayMs 8000', async () => {
    const { useSettings, SettingsProvider } = await getHook()
    const wrapper = ({ children }: { children: React.ReactNode }) =>
      React.createElement(SettingsProvider, null, children)
    const { result } = renderHook(() => useSettings(), { wrapper })
    expect(result.current.settings.cardDisplayMs).toBe(8000)
  })

  it('returns default maxCards 3', async () => {
    const { useSettings, SettingsProvider } = await getHook()
    const wrapper = ({ children }: { children: React.ReactNode }) =>
      React.createElement(SettingsProvider, null, children)
    const { result } = renderHook(() => useSettings(), { wrapper })
    expect(result.current.settings.maxCards).toBe(3)
  })
})

describe('useSettings — localStorage persistence', () => {
  it('reads maxCards from localStorage on init', async () => {
    localStorageMock.getItem.mockImplementation((key: string) =>
      key === 'nhl_overlay_settings' ? JSON.stringify({ maxCards: 5 }) : null
    )
    const { useSettings, SettingsProvider } = await getHook()
    const wrapper = ({ children }: { children: React.ReactNode }) =>
      React.createElement(SettingsProvider, null, children)
    const { result } = renderHook(() => useSettings(), { wrapper })
    expect(result.current.settings.maxCards).toBe(5)
  })

  it('reads cardDisplayMs from localStorage on init', async () => {
    localStorageMock.getItem.mockImplementation((key: string) =>
      key === 'nhl_overlay_settings' ? JSON.stringify({ cardDisplayMs: 12000 }) : null
    )
    const { useSettings, SettingsProvider } = await getHook()
    const wrapper = ({ children }: { children: React.ReactNode }) =>
      React.createElement(SettingsProvider, null, children)
    const { result } = renderHook(() => useSettings(), { wrapper })
    expect(result.current.settings.cardDisplayMs).toBe(12000)
  })

  it('falls back to defaults for keys not in localStorage', async () => {
    localStorageMock.getItem.mockImplementation((key: string) =>
      key === 'nhl_overlay_settings' ? JSON.stringify({ maxCards: 1 }) : null
    )
    const { useSettings, SettingsProvider } = await getHook()
    const wrapper = ({ children }: { children: React.ReactNode }) =>
      React.createElement(SettingsProvider, null, children)
    const { result } = renderHook(() => useSettings(), { wrapper })
    expect(result.current.settings.maxCards).toBe(1)
    expect(result.current.settings.cardDisplayMs).toBe(8000)
  })

  it('writes to localStorage when updateSetting is called', async () => {
    const { useSettings, SettingsProvider } = await getHook()
    const wrapper = ({ children }: { children: React.ReactNode }) =>
      React.createElement(SettingsProvider, null, children)
    const { result } = renderHook(() => useSettings(), { wrapper })
    act(() => { result.current.updateSetting('maxCards', 5) })
    expect(localStorageMock.setItem).toHaveBeenCalledWith(
      'nhl_overlay_settings',
      expect.stringContaining('"maxCards":5')
    )
  })

  it('updateSetting updates the settings value in state', async () => {
    const { useSettings, SettingsProvider } = await getHook()
    const wrapper = ({ children }: { children: React.ReactNode }) =>
      React.createElement(SettingsProvider, null, children)
    const { result } = renderHook(() => useSettings(), { wrapper })
    act(() => { result.current.updateSetting('maxCards', 5) })
    expect(result.current.settings.maxCards).toBe(5)
  })
})

describe('useSettings — backend POST', () => {
  it('calls POST /settings on mount', async () => {
    const { useSettings, SettingsProvider } = await getHook()
    const wrapper = ({ children }: { children: React.ReactNode }) =>
      React.createElement(SettingsProvider, null, children)
    renderHook(() => useSettings(), { wrapper })
    await act(async () => { await Promise.resolve() })
    expect(fetchMock).toHaveBeenCalledWith('/settings', expect.objectContaining({ method: 'POST' }))
  })

  it('POSTs only backend-bound keys (not cardDisplayMs or maxCards)', async () => {
    const { useSettings, SettingsProvider } = await getHook()
    const wrapper = ({ children }: { children: React.ReactNode }) =>
      React.createElement(SettingsProvider, null, children)
    renderHook(() => useSettings(), { wrapper })
    await act(async () => { await Promise.resolve() })
    const body = JSON.parse(fetchMock.mock.calls[0][1].body as string)
    expect(body).not.toHaveProperty('cardDisplayMs')
    expect(body).not.toHaveProperty('maxCards')
    expect(body).toHaveProperty('model')
    expect(body).toHaveProperty('language')
    expect(body).toHaveProperty('fuzzy_ngram_threshold')
    expect(body).toHaveProperty('fuzzy_partial_threshold')
    expect(body).toHaveProperty('cache_ttl')
  })

  it('calls POST /settings when a backend-bound setting changes', async () => {
    const { useSettings, SettingsProvider } = await getHook()
    const wrapper = ({ children }: { children: React.ReactNode }) =>
      React.createElement(SettingsProvider, null, children)
    const { result } = renderHook(() => useSettings(), { wrapper })
    await act(async () => { await Promise.resolve() })
    fetchMock.mockClear()
    act(() => { result.current.updateSetting('language', 'fr') })
    await act(async () => { await Promise.resolve() })
    expect(fetchMock).toHaveBeenCalledWith('/settings', expect.objectContaining({ method: 'POST' }))
  })

  it('does NOT call POST /settings when a frontend-only setting changes', async () => {
    const { useSettings, SettingsProvider } = await getHook()
    const wrapper = ({ children }: { children: React.ReactNode }) =>
      React.createElement(SettingsProvider, null, children)
    const { result } = renderHook(() => useSettings(), { wrapper })
    await act(async () => { await Promise.resolve() })
    fetchMock.mockClear()
    act(() => { result.current.updateSetting('maxCards', 5) })
    await act(async () => { await Promise.resolve() })
    expect(fetchMock).not.toHaveBeenCalled()
  })
})
