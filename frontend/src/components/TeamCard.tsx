import { useEffect, useState } from 'react'
import type { TeamPayload } from '../types/payloads'

function ordinal(n: number): string {
  const mod100 = n % 100
  if (mod100 >= 11 && mod100 <= 13) return 'th'
  const mod10 = n % 10
  if (mod10 === 1) return 'st'
  if (mod10 === 2) return 'nd'
  if (mod10 === 3) return 'rd'
  return 'th'
}

type Props = { payload: TeamPayload; onExpire: () => void }

export function TeamCard({ payload, onExpire }: Props) {
  const [imgError, setImgError] = useState(false)
  const [isExiting, setIsExiting] = useState(false)

  useEffect(() => {
    let inner: ReturnType<typeof setTimeout>
    const outer = setTimeout(() => {
      setIsExiting(true)
      inner = setTimeout(onExpire, 200)
    }, 8000)
    return () => {
      clearTimeout(outer)
      clearTimeout(inner)
    }
  }, [onExpire])

  const divRank = `${payload.division_rank}${ordinal(payload.division_rank)}`
  const confRank = `${payload.conference_rank}${ordinal(payload.conference_rank)}`

  return (
    <div className={`w-[280px] bg-black/80 rounded-lg p-4 ${isExiting ? 'card-exit' : 'card-enter'}`}>
      <div className="flex items-center gap-3">
        {imgError ? (
          <div className="w-12 h-12 rounded-lg bg-gray-700 flex items-center justify-center text-amber-400 text-sm font-bold flex-shrink-0">
            {payload.abbrev}
          </div>
        ) : (
          <img
            src={payload.logo_url}
            alt={payload.name}
            className="w-12 h-12 rounded-lg object-contain flex-shrink-0"
            onError={() => setImgError(true)}
          />
        )}
        <div className="flex-1 min-w-0">
          <div className="text-white font-bold text-[18px] truncate">{payload.name}</div>
          <div className="text-gray-400 text-[13px]">Div: {divRank} · Conf: {confRank}</div>
        </div>
      </div>
      <div className="border-t border-gray-700 mt-3 pt-3">
        <div className="flex gap-4">
          <span className="text-white font-semibold text-[16px]">{payload.stats.wins}W</span>
          <span className="text-white font-semibold text-[16px]">{payload.stats.losses}L</span>
          <span className="text-white font-semibold text-[16px]">{payload.stats.ot_losses}OT</span>
          <span className="text-amber-400 font-semibold text-[16px]">{payload.stats.points} PTS</span>
        </div>
      </div>
    </div>
  )
}
