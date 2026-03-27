export type PlayerPayload = {
  type: 'player'
  id: number
  name: string
  team: string
  position: string
  headshot_url: string
  stats: {
    season: string
    games_played: number
    goals: number
    assists: number
    points: number
    plus_minus: number
  }
  display: string
  ts: number
}

export type GoaliePayload = {
  type: 'goalie'
  id: number
  name: string
  team: string
  headshot_url: string
  stats: {
    season: string
    games_played: number
    wins: number
    losses: number
    ot_losses: number
    save_percentage: number
    goals_against_avg: number
    shutouts: number
  }
  display: string
  ts: number
}

export type TeamPayload = {
  type: 'team'
  name: string
  abbrev: string
  logo_url: string
  stats: {
    season: string
    wins: number
    losses: number
    ot_losses: number
    points: number
    games_played: number
    goals_for: number
    goals_against: number
    point_pct: number
  }
  conference_rank: number
  division_rank: number
  display: string
  ts: number
}

export type TriggerPayload = {
  type: 'trigger'
  id: string
  keywords: string[]
  description: string
  fields: { label: string; value: string | number | null }[]
  display: string
  ts: number
}

export type SystemPayload = {
  type: 'system'
  event: 'connected' | 'disconnected' | 'transcriber_ready' | 'transcriber_error'
  message: string
  ts: number
}

export type StatPayload =
  | PlayerPayload
  | GoaliePayload
  | TeamPayload
  | TriggerPayload
  | SystemPayload

export type Envelope = {
  v: 1
  payload: StatPayload
}
