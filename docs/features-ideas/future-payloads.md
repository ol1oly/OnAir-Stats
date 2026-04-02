# Future Payload Types — Idea Space

> Idea backlog and extension checklist for future overlay card types and trigger display variants.

This document tracks ideas for new overlay card types and trigger display variants. It is intentionally open-ended: add rough ideas freely. When an idea matures into a concrete plan, promote it to `task.md`.

---

## Adding a New Card Type — Checklist

When implementing any new `StatPayload` discriminator:

1. Add `NewPayload` type to `frontend/src/types/payloads.ts` and extend the `StatPayload` union
2. Create `frontend/src/components/NewCard.tsx` (slide-in animation, 8s auto-dismiss, unique accent color)
3. Register in `OverlayCanvas.tsx` `CardWrapper` render block (the `payload.type` switch)
4. Add `build_new_payload()` in `backend/stats.py`
5. Wire the emit path in `server.py` `_handle_transcript()` (or `trigger_runner.py` if trigger-driven)
6. Add backend unit tests in `backend/tests/test_stats.py`
7. Add frontend unit tests in `frontend/src/components/__tests__/NewCard.test.tsx`

---

## Future Card Type Ideas

| Type discriminator | Description | NHL API source | Status |
|---|---|---|---|
| `"score"` | Current game score, period, time remaining | `/score/now` or `/gamecenter/{gameId}/landing` | idea |
| `"schedule"` | Next game date, opponent, arena, broadcast | `/club-schedule/{team}/week/now` | idea |
| `"injury"` | Player injury status and estimated return | `/roster/{team}/current` | idea |
| `"milestone"` | Season milestone approaching (e.g. 99th point, 500th goal) | derived from `get_player()` stats | idea |
| *(add ideas here)* | | | |

---

## Trigger Display Variants

Ideas for alternate `TriggerCard` layouts beyond the default label/value list. The `display_type` field would be added to `TriggerPayload` and `TriggerRecord` to select the renderer.

| Variant | `display_type` value | Description | Status |
|---|---|---|---|
| Label/value list | `"list"` (default) | Generic stacked rows — always works for any field set | **MVP (implemented)** |
| HTML template | `"html"` | LLM-generated or user-authored HTML; DOMPurify-sanitized before render | specced in `trigger-builder.md` |
| Comparison bar | `"comparison"` | Two values side-by-side with a visual ratio bar (e.g. team A vs B stat) | idea |
| Stat table | `"table"` | Multi-row tabular display for array-valued fields (e.g. top 3 PP scorers) | idea |
| Sparkline | `"sparkline"` | Mini trend line for time-series data (e.g. last 10 games goals) | idea |
| *(add ideas here)* | | | |

When implementing a new variant:
1. Add `display_type` to `TriggerPayload` in `payloads.ts` (optional, defaults to `"list"`)
2. Add `display_type` to `TriggerRecord` TypedDict in `trigger_store.py`
3. Add a renderer branch in `TriggerCard.tsx`
4. The LLM resolver prompt should be extended to declare the appropriate `display_type` based on the description
