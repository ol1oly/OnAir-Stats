# docs/

Reference material, specs, and planning docs for the NHL Radio Overlay. Keep this index up to date whenever a new file is added here.

## api/
NHL API specs and the WebSocket payload contract.
- `nhlAPIDocumentation.md` — unofficial reference for both NHL APIs (api-web.nhle.com and api.nhle.com/stats)
- `new-api.md` — discovered endpoints for the newer api-web.nhle.com v1 API
- `ws-payload-contract.md` — WebSocket message shapes; single source of truth for the frontend/backend contract

## project/
Planning, tasks, and feature specs.
- `plan.md` — architecture decisions and stack rationale
- `task.md` — atomic task list with build progress
- `trigger-builder.md` — full spec for the custom trigger system (MVP + post-MVP)
- `future-payloads.md` — idea backlog for new card types and trigger display variants

## superpowers/
AI-generated plans and design specs (created by Claude).
- `specs/2026-03-27-card-images-design.md` — design spec for player headshots and team logos
- `plans/2026-03-27-card-images.md` — implementation plan for the card images feature

## Root files
- `frontend-design.md` — frontend architecture and component breakdown
- `notes.md` — freeform notes and feature ideas not yet in the task list
