import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { SettingsSlider } from '../SettingsSlider'

const stops = [
  { label: 'Low', value: 15 },
  { label: 'Medium', value: 45 },
  { label: 'High', value: 120 },
  { label: 'Max', value: 300 },
]

describe('SettingsSlider — rendering', () => {
  it('renders the label', () => {
    render(<SettingsSlider label="Cache TTL" description="How long to cache stats" stops={stops} value={45} onChange={vi.fn()} />)
    expect(screen.getByText('Cache TTL')).toBeTruthy()
  })

  it('renders the description', () => {
    render(<SettingsSlider label="Cache TTL" description="How long to cache stats" stops={stops} value={45} onChange={vi.fn()} />)
    expect(screen.getByText('How long to cache stats')).toBeTruthy()
  })

  it('renders the current stop label', () => {
    render(<SettingsSlider label="Cache TTL" description="How long to cache stats" stops={stops} value={45} onChange={vi.fn()} />)
    expect(screen.getByText('Medium')).toBeTruthy()
  })

  it('renders a range input', () => {
    render(<SettingsSlider label="Cache TTL" description="How long to cache stats" stops={stops} value={45} onChange={vi.fn()} />)
    expect(screen.getByRole('slider')).toBeTruthy()
  })

  it('slider min is 0', () => {
    render(<SettingsSlider label="Cache TTL" description="How long to cache stats" stops={stops} value={45} onChange={vi.fn()} />)
    expect((screen.getByRole('slider') as HTMLInputElement).min).toBe('0')
  })

  it('slider max equals stops.length - 1', () => {
    render(<SettingsSlider label="Cache TTL" description="How long to cache stats" stops={stops} value={45} onChange={vi.fn()} />)
    expect((screen.getByRole('slider') as HTMLInputElement).max).toBe('3')
  })

  it('slider step is 1', () => {
    render(<SettingsSlider label="Cache TTL" description="How long to cache stats" stops={stops} value={45} onChange={vi.fn()} />)
    expect((screen.getByRole('slider') as HTMLInputElement).step).toBe('1')
  })

  it('slider value is the index of the current stop', () => {
    render(<SettingsSlider label="Cache TTL" description="How long to cache stats" stops={stops} value={120} onChange={vi.fn()} />)
    expect((screen.getByRole('slider') as HTMLInputElement).value).toBe('2')
  })

  it('defaults to index 0 when value does not match any stop', () => {
    render(<SettingsSlider label="Cache TTL" description="How long to cache stats" stops={stops} value={999} onChange={vi.fn()} />)
    expect((screen.getByRole('slider') as HTMLInputElement).value).toBe('0')
  })
})

describe('SettingsSlider — interaction', () => {
  it('calls onChange with the stop value when slider moves', () => {
    const onChange = vi.fn()
    render(<SettingsSlider label="Cache TTL" description="How long to cache stats" stops={stops} value={15} onChange={onChange} />)
    fireEvent.change(screen.getByRole('slider'), { target: { value: '2' } })
    expect(onChange).toHaveBeenCalledWith(120)
  })

  it('calls onChange with the first stop value when slider is at 0', () => {
    const onChange = vi.fn()
    render(<SettingsSlider label="Cache TTL" description="How long to cache stats" stops={stops} value={45} onChange={onChange} />)
    fireEvent.change(screen.getByRole('slider'), { target: { value: '0' } })
    expect(onChange).toHaveBeenCalledWith(15)
  })

  it('shows updated stop label after value changes', () => {
    const { rerender } = render(<SettingsSlider label="Cache TTL" description="How long to cache stats" stops={stops} value={15} onChange={vi.fn()} />)
    expect(screen.getByText('Low')).toBeTruthy()
    rerender(<SettingsSlider label="Cache TTL" description="How long to cache stats" stops={stops} value={300} onChange={vi.fn()} />)
    expect(screen.getByText('Max')).toBeTruthy()
  })
})
