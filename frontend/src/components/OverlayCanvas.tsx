import { useCallback, useEffect, useRef, useState } from 'react'
import { WS_OVERLAY_URL, MAX_CARDS, DEDUP_MS, CARD_DISPLAY_MS, CARD_EXIT_MS } from '../config'
import { useOverlaySocket } from '../hooks/useOverlaySocket'
import type { StatPayload } from '../types/payloads'
import { StatCard } from './StatCard'
import { GoalieCard } from './GoalieCard'
import { TeamCard } from './TeamCard'
const DEBUG = new URLSearchParams(location.search).has('debug')

type CardItem = { id: string; payload: StatPayload; resetKey: number }

function entityKey(p: StatPayload): string {
  if (p.type === 'player' || p.type === 'goalie') return `${p.type}_${p.id}`
  if (p.type === 'team') return `team_${p.abbrev}`
  if (p.type === 'trigger') return `trigger_${p.id}`
  return 'system'
}

function cardId(p: StatPayload): string {
  if (p.type === 'player' || p.type === 'goalie') return `${p.type}_${p.id}_${p.ts}`
  if (p.type === 'team') return `team_${p.abbrev}_${p.ts}`
  if (p.type === 'trigger') return `trigger_${p.id}_${p.ts}`
  return `system_${p.ts}`
}

// ---------------------------------------------------------------------------
// DebugCountdown — isolated so only this re-renders every second
// ---------------------------------------------------------------------------

function DebugCountdown({ resetKey }: { resetKey: number }) {
  const [secondsLeft, setSecondsLeft] = useState(CARD_DISPLAY_MS / 1000)
  useEffect(() => {
    setSecondsLeft(CARD_DISPLAY_MS / 1000)
    const interval = setInterval(() => setSecondsLeft(s => s - 1), 1000)
    return () => clearInterval(interval)
  }, [resetKey])
  return (
    <span className="absolute top-1 right-2 text-gray-500 text-[11px] tabular-nums pointer-events-none">
      {secondsLeft}s
    </span>
  )
}

// ---------------------------------------------------------------------------
// CardWrapper — owns the 8s timer; renders card + optional debug badge
// ---------------------------------------------------------------------------

type CardWrapperProps = {
  item: CardItem
  removeCard: (id: string) => void
  resetCard: (id: string) => void
  debug: boolean
}

function CardWrapper({ item, removeCard, resetCard, debug }: CardWrapperProps) {
  const [isExiting, setIsExiting] = useState(false)
  const onExpire = useCallback(() => removeCard(item.id), [removeCard, item.id])

  useEffect(() => {
    setIsExiting(false)
    const outer = setTimeout(() => {
      setIsExiting(true)
      setTimeout(onExpire, CARD_EXIT_MS)
    }, CARD_DISPLAY_MS)
    return () => clearTimeout(outer)
  }, [item.resetKey, onExpire])

  const handleClick = useCallback(() => resetCard(item.id), [resetCard, item.id])
  const { id, payload } = item

  return (
    <div className="relative cursor-pointer" onClick={handleClick}>
      {payload.type === 'player' && <StatCard key={id} payload={payload} isExiting={isExiting} />}
      {payload.type === 'goalie' && <GoalieCard key={id} payload={payload} isExiting={isExiting} />}
      {payload.type === 'team' && <TeamCard key={id} payload={payload} isExiting={isExiting} />}
      {debug && <DebugCountdown resetKey={item.resetKey} />}
    </div>
  )
}

// ---------------------------------------------------------------------------
// OverlayCanvas
// ---------------------------------------------------------------------------

export function OverlayCanvas() {
  const { latestPayload } = useOverlaySocket(WS_OVERLAY_URL)
  const [cards, setCards] = useState<CardItem[]>([])
  const seenRef = useRef<Map<string, number>>(new Map())

  const removeCard = useCallback((id: string) => {
    setCards(prev => prev.filter(c => c.id !== id))
  }, [])

  const resetCard = useCallback((id: string) => {
    setCards(prev => prev.map(c => c.id === id ? { ...c, resetKey: c.resetKey + 1 } : c))
  }, [])

  useEffect(() => {
    if (!latestPayload || latestPayload.type === 'system') return

    const key = entityKey(latestPayload)
    const now = Date.now()
    const lastSeen = seenRef.current.get(key) ?? 0

    setCards(prev => {
      const existingIdx = prev.findIndex(c => entityKey(c.payload) === key)
      if (existingIdx !== -1) {
        // Card is active — reset its timer instead of adding a duplicate
        const updated = [...prev]
        updated[existingIdx] = { ...updated[existingIdx], resetKey: updated[existingIdx].resetKey + 1 }
        return updated
      }
      if (now - lastSeen < DEDUP_MS) return prev
      const next = [...prev, { id: cardId(latestPayload), payload: latestPayload, resetKey: 0 }]
      return next.length > MAX_CARDS ? next.slice(next.length - MAX_CARDS) : next
    })
    seenRef.current.set(key, now)
  }, [latestPayload])

  return (
    <div className="absolute bottom-8 left-8 flex flex-col-reverse gap-3">
      {cards.map(item => (
        <CardWrapper key={item.id} item={item} removeCard={removeCard} resetCard={resetCard} debug={DEBUG} />
      ))}
    </div>
  )
}
