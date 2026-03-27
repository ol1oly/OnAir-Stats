import { useCallback, useEffect, useRef, useState } from 'react'
import { useOverlaySocket } from '../hooks/useOverlaySocket'
import type { StatPayload } from '../types/payloads'
import { StatCard } from './StatCard'
import { GoalieCard } from './GoalieCard'
import { TeamCard } from './TeamCard'

const WS_URL = 'ws://localhost:8000/ws'
const MAX_CARDS = 3
const DEDUP_MS = 2000

type CardItem = { id: string; payload: StatPayload }

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

export function OverlayCanvas() {
  const { latestPayload } = useOverlaySocket(WS_URL)
  const [cards, setCards] = useState<CardItem[]>([])
  const seenRef = useRef<Map<string, number>>(new Map())

  const removeCard = useCallback((id: string) => {
    setCards(prev => prev.filter(c => c.id !== id))
  }, [])

  useEffect(() => {
    if (!latestPayload || latestPayload.type === 'system') return

    const key = entityKey(latestPayload)
    const now = Date.now()
    if (now - (seenRef.current.get(key) ?? 0) < DEDUP_MS) return
    seenRef.current.set(key, now)

    setCards(prev => {
      const next = [...prev, { id: cardId(latestPayload), payload: latestPayload }]
      return next.length > MAX_CARDS ? next.slice(next.length - MAX_CARDS) : next
    })
  }, [latestPayload])

  return (
    <div className="absolute bottom-8 left-8 flex flex-col-reverse gap-3">
      {cards.map(({ id, payload }) => {
        if (payload.type === 'player') return <StatCard key={id} payload={payload} onExpire={() => removeCard(id)} />
        if (payload.type === 'goalie') return <GoalieCard key={id} payload={payload} onExpire={() => removeCard(id)} />
        if (payload.type === 'team') return <TeamCard key={id} payload={payload} onExpire={() => removeCard(id)} />
        return null
      })}
    </div>
  )
}
