import { useEffect, useState } from 'react'
import type { GoaliePayload } from '../types/payloads'

function initials(name: string): string {
  const parts = name.trim().split(' ')
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase()
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase()
}

type Props = { payload: GoaliePayload; onExpire: () => void }

export function GoalieCard({ payload, onExpire }: Props) {
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

  const svPct = payload.stats.save_percentage.toFixed(3).replace(/^0\./, '.')
  const gaa = payload.stats.goals_against_avg.toFixed(2)
  const { wins, losses, ot_losses, shutouts } = payload.stats

  return (
    <div className={`w-[280px] bg-black/80 rounded-lg p-4 ${isExiting ? 'card-exit' : 'card-enter'}`}>
      <div className="flex items-center gap-2.5">
        {imgError ? (
          <div className="w-10 h-10 rounded-full bg-gray-700 flex items-center justify-center text-white text-xs font-bold flex-shrink-0">
            {initials(payload.name)}
          </div>
        ) : (
          <img
            src={payload.headshot_url}
            alt={payload.name}
            className="w-10 h-10 rounded-full object-cover flex-shrink-0"
            onError={() => setImgError(true)}
          />
        )}
        <div className="flex-1 min-w-0">
          <div className="flex items-baseline justify-between">
            <span className="text-white font-bold text-[18px] truncate">{payload.name}</span>
            <span className="text-gray-400 text-[13px] ml-2 flex-shrink-0">{payload.team}</span>
          </div>
          <div className="text-cyan-400 text-[13px]">G</div>
        </div>
      </div>
      <div className="border-t border-gray-700 mt-3 pt-3">
        <div className="flex gap-4">
          <span>
            <span className="text-cyan-400 font-semibold text-[16px]">{svPct}</span>
            <span className="text-gray-400 text-[13px] ml-1">SV%</span>
          </span>
          <span>
            <span className="text-cyan-400 font-semibold text-[16px]">{gaa}</span>
            <span className="text-gray-400 text-[13px] ml-1">GAA</span>
          </span>
          <span>
            <span className="text-cyan-400 font-semibold text-[16px]">{shutouts}</span>
            <span className="text-gray-400 text-[13px] ml-1">SO</span>
          </span>
        </div>
        <div className="text-white text-[14px] mt-1">{wins}W {losses}L {ot_losses}OT</div>
      </div>
    </div>
  )
}
