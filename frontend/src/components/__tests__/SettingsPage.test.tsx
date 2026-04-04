import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import React from 'react'
import { SettingsPage } from '../../pages/SettingsPage'
import { SettingsProvider } from '../../contexts/SettingsContext'

vi.mock('wouter', () => ({
  Link: ({ href, children, className }: { href: string; children: React.ReactNode; className?: string }) =>
    React.createElement('a', { href, className }, children),
  useLocation: () => ['/', vi.fn()],
}))

const fetchMock = vi.fn(() =>
  Promise.resolve({ ok: true, json: () => Promise.resolve({ ok: true }) } as Response)
)

const localStorageMock = (() => {
  let store: Record<string, string> = {}
  return {
    getItem: vi.fn((key: string) => store[key] ?? null),
    setItem: vi.fn((key: string, value: string) => { store[key] = value }),
    removeItem: vi.fn((key: string) => { delete store[key] }),
    clear: vi.fn(() => { store = {} }),
  }
})()

beforeEach(() => {
  localStorageMock.clear()
  localStorageMock.getItem.mockClear()
  localStorageMock.setItem.mockClear()
  fetchMock.mockClear()
  vi.stubGlobal('localStorage', localStorageMock)
  vi.stubGlobal('fetch', fetchMock)
})

afterEach(() => {
  vi.unstubAllGlobals()
})

function renderSettingsPage() {
  return render(
    React.createElement(SettingsProvider, null, React.createElement(SettingsPage))
  )
}

describe('SettingsPage — renders all sliders', () => {
  it('renders Deepgram Model slider', () => {
    renderSettingsPage()
    expect(screen.getByText('Deepgram Model')).toBeTruthy()
  })

  it('renders Broadcast Language slider', () => {
    renderSettingsPage()
    expect(screen.getByText('Broadcast Language')).toBeTruthy()
  })

  it('renders Name Matching Sensitivity slider', () => {
    renderSettingsPage()
    expect(screen.getByText('Name Matching Sensitivity')).toBeTruthy()
  })

  it('renders Stats Cache TTL slider', () => {
    renderSettingsPage()
    expect(screen.getByText('Stats Cache TTL')).toBeTruthy()
  })

  it('renders Card Display Duration slider', () => {
    renderSettingsPage()
    expect(screen.getByText('Card Display Duration')).toBeTruthy()
  })

  it('renders Max Visible Cards slider', () => {
    renderSettingsPage()
    expect(screen.getByText('Max Visible Cards')).toBeTruthy()
  })
})

describe('SettingsPage — default values displayed', () => {
  it('shows Nova-2 as default model', () => {
    renderSettingsPage()
    expect(screen.getByText('Nova-2')).toBeTruthy()
  })

  it('shows English as default language', () => {
    renderSettingsPage()
    expect(screen.getByText('English')).toBeTruthy()
  })

  it('shows Balanced as default sensitivity', () => {
    renderSettingsPage()
    expect(screen.getByText('Balanced')).toBeTruthy()
  })

  it('shows 45 s as default cache TTL', () => {
    renderSettingsPage()
    expect(screen.getByText('45 s')).toBeTruthy()
  })

  it('shows 8 s as default card display duration', () => {
    renderSettingsPage()
    expect(screen.getByText('8 s')).toBeTruthy()
  })

  it('shows 3 as default max visible cards', () => {
    renderSettingsPage()
    expect(screen.getByText('3')).toBeTruthy()
  })
})

describe('SettingsPage — slider interaction', () => {
  it('moving Max Visible Cards slider to 0 writes 1 card to localStorage', () => {
    renderSettingsPage()
    const sliders = screen.getAllByRole('slider')
    fireEvent.change(sliders[5], { target: { value: '0' } })
    expect(localStorageMock.setItem).toHaveBeenCalledWith(
      'nhl_overlay_settings',
      expect.stringContaining('"maxCards":1')
    )
  })

  it('moving Cache TTL slider to index 2 writes 120 to localStorage', () => {
    renderSettingsPage()
    const sliders = screen.getAllByRole('slider')
    fireEvent.change(sliders[3], { target: { value: '2' } })
    expect(localStorageMock.setItem).toHaveBeenCalledWith(
      'nhl_overlay_settings',
      expect.stringContaining('"cacheTtl":120')
    )
  })

  it('moving Language slider to index 1 triggers backend POST with language fr', async () => {
    renderSettingsPage()
    await new Promise(r => setTimeout(r, 0))
    fetchMock.mockClear()
    const sliders = screen.getAllByRole('slider')
    fireEvent.change(sliders[1], { target: { value: '1' } })
    await new Promise(r => setTimeout(r, 0))
    expect(fetchMock).toHaveBeenCalledWith('/settings', expect.objectContaining({ method: 'POST' }))
    const body = JSON.parse((fetchMock.mock.calls as any)[0][1].body as string)
    expect(body.language).toBe('fr')
  })
})
