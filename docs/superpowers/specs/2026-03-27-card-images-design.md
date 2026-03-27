# Card Images Design Spec

**Date:** 2026-03-27
**Scope:** Add player headshots to StatCard/GoalieCard and team logos to TeamCard

---

## Summary

Player and goalie stat cards will display a circular player headshot inline with the player name in the card header. Team cards will display the team logo in place of the large abbreviation, with the full team name beside it.

No backend changes are required — `headshot_url` and `logo_url` are already present in all relevant payloads.

---

## Player / Goalie Cards — Circular Avatar in Header

### Layout

```
┌────────────────────────────────────┐
│  [●] Connor McDavid          EDM   │  ← 40px circle + name (bold, white) + team (muted)
│      C · #97                       │  ← position row, indented to align under name
├────────────────────────────────────┤
│  32 G    100 A    132 PTS          │  ← stats row (unchanged)
│  +15                               │
└────────────────────────────────────┘
```

- Image: `<img src={payload.headshot_url} />` — `w-10 h-10 rounded-full object-cover flex-shrink-0`
- Source: `https://assets.nhle.com/mugs/nhl/skater/{id}.png` (already in payload)
- Header becomes a flex row: `[avatar] [name/position column] [team abbrev]`
- Name column uses `min-w-0` + `truncate` to prevent overflow on long names
- GoalieCard gets identical treatment (same layout, cyan accent unchanged)

### Fallback

On `onError`: replace `<img>` with a 40px circle (`bg-gray-700 rounded-full`) showing the player's initials (first letter of first name + first letter of last name) in white, 12px, centered.

---

## Team Card — Logo Replaces Abbreviation

### Layout

```
┌────────────────────────────────────┐
│  [■] Edmonton Oilers               │  ← 52px rounded logo + full team name (bold, white)
│      Div: 2nd · Conf: 3rd          │  ← rankings row, indented to align under name
├────────────────────────────────────┤
│  42W   20L   5OT     89 PTS        │  ← record + points (unchanged)
└────────────────────────────────────┘
```

- Image: `<img src={payload.logo_url} />` — `w-12 h-12 rounded-lg object-contain flex-shrink-0`
- Source: `https://assets.nhle.com/logos/nhl/svg/{abbrev}_light.svg` (already in payload)
- The large amber abbreviation (`EDM`) is removed from the header — the logo is the primary identifier
- Full team name (`Edmonton Oilers`) remains beside the logo, bold white
- Rankings row (`Div: 2nd · Conf: 3rd`) moves to a sub-row indented under the name
- Stats row below the divider is unchanged

### Fallback

On `onError`: replace `<img>` with a 48px square (`bg-gray-700 rounded-lg`) showing the team abbreviation in amber (`text-amber-400`), 14px bold, centered.

---

## Files Changed

| File | Change |
|---|---|
| `frontend/src/components/StatCard.tsx` | Add 40px circular avatar to header row |
| `frontend/src/components/GoalieCard.tsx` | Add 40px circular avatar to header row (identical to StatCard) |
| `frontend/src/components/TeamCard.tsx` | Replace amber abbreviation header with logo + full name |
| `docs/frontend-design.md` | Update layout ASCII diagrams for all three cards |
| `docs/project/task.md` | Promote OPT-04 to main task list, add implementation detail |

No changes to: backend, payload types, hooks, `OverlayCanvas`, animations.

---

## Constraints

- Card width stays at 280px. With the 40px avatar + 10px gap in player cards, the text column has ~198px — sufficient for most names; long names truncated with ellipsis.
- SVG logos use `object-contain` so the logo fills the box without clipping regardless of aspect ratio.
- Both fallback states match the card's existing color language (gray placeholder, initials/abbrev in the card's accent color).
