# Notes

---

## Keyword-based action extraction in `extract_entities`

**Date:** 2026-03-24

Currently `extract_entities` returns players and teams only:

```python
{"players": ["Connor McDavid"], "teams": ["TOR"]}
```

**Idea:** add an `actions` field by detecting hockey-action keywords in the transcript. For example:

> *"McDavid scores tonight against the Leafs"*

could return:

```python
{"players": ["Connor McDavid"], "teams": ["TOR"], "actions": ["scoring"]}
```

### Potential keyword groups

| Action | Keywords |
|---|---|
| `scoring` | scores, scored, goal, buries, taps in, fires, buries it, snaps |
| `assist` | assists, sets up, feeds, dishes, pass, thread |
| `penalty` | penalty, hooking, tripping, slashing, interference, high-sticking |
| `fight` | fight, drops the gloves, scrap, tilt |
| `save` | save, stops, robs, denies, kicks out |
| `hit` | hit, crushes, lays out, boards |

### Usage in the pipeline

The `actions` field could be used by the server to:
- Prioritize which stat card to show (e.g. show goals stat when action is `scoring`)
- Trigger specific overlays (e.g. a fight card, or a goalie save highlight)
- Filter out low-signal mentions (e.g. a player name mentioned in passing with no action)

### Implementation sketch

A simple pass over the tokenized transcript checking for keyword membership — no fuzzy matching needed since these are common English words. Could be a `set`-based lookup added at the end of `extract_entities`, returning `[]` if no keywords matched.
