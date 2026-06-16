---
name: worldcup
version: 1.0.0
description: |
  FIFA World Cup 2026 — match schedules, live scores, results, and the prediction game (place/cancel bets with points, betting stats, leaderboard).

  Use whenever the user mentions the World Cup: today's / upcoming / live / finished matches, a specific match, placing or cancelling a prediction, staking points, their betting balance or win rate, or the predictor leaderboard.
author: starchild
tags: [worldcup, fifa, football, soccer, matches, prediction, betting, leaderboard, 2026]
delivery: script
metadata:
  starchild:
    emoji: "⚽"
    skillKey: worldcup
---

# ⚽ World Cup 2026 Skill

FIFA World Cup 2026 data + the points-based prediction game. **Script skill** —
call the functions in `core.skill_tools.worldcup` from bash and read the JSON.
Auth is automatic (container JWT); no API key needed.

## How to call

```bash
python3 -c "from core.skill_tools import worldcup; import json; print(json.dumps(worldcup.get_today_matches()))"
```

Every function returns a dict like `{"success": true, "data": ...}` (or
`{"success": false, "error": ...}` on failure).

## When to use

- **Matches** — today / upcoming / live / finished, or one specific match.
- **Predictions** — place, cancel, or review prediction history.
- **Stats** — point balance, betting limits, win rate, total staked.
- **Leaderboard** — top predictors by points or accuracy.

## Functions (`from core.skill_tools import worldcup`)

| Function | Returns |
|----------|---------|
| `get_today_matches()` | today's matches + your prediction status |
| `get_upcoming_matches(limit=10)` | next scheduled matches |
| `get_live_matches()` | matches in progress now |
| `get_finished_matches(limit=20)` | recent results |
| `get_match_detail(match_id)` | one match in full |
| `place_bet(match_id, predict_type, prediction, stake)` | places a prediction |
| `cancel_prediction(prediction_id)` | cancels an unsettled prediction, refunds stake |
| `get_betting_status()` | point balance, pending stakes, min/max stake |
| `get_my_predictions(match_id=None, settled_only=False)` | your prediction history |
| `get_prediction_detail(prediction_id)` | one prediction in full |
| `get_my_stats()` | your win rate, total staked, etc. |
| `get_leaderboard(limit=50, sort_by="points")` | top predictors (`sort_by`: points\|accuracy) |

## Placing a bet — `predict_type` and `prediction`

`prediction` is a dict whose shape depends on `predict_type`. Fill ONLY the keys
for that type:

| predict_type | prediction | meaning |
|---|---|---|
| `win_draw_loss` | `{"choice": "home"\|"draw"\|"away"}` | match result |
| `exact_score` | `{"home": N, "away": N}` | exact final score |
| `total_goals` | `{"range": "0-1"\|"2-3"\|"4+"}` | total goals bucket |
| `first_goal` | `{"team": "TEAM_CODE"}` | which team scores first (e.g. `BRA`) |

`stake` = points to wager: multiple of 10, min 10, max 10000.

### Recommended place_bet flow
1. `get_betting_status()` — confirm enough available points.
2. `get_match_detail(match_id)` or `get_today_matches()` — confirm the match is open and get team codes (needed for `first_goal`).
3. `place_bet(match_id, predict_type, prediction, stake)`.
4. Read back the returned prediction ID to the user.

Example:
```bash
python3 -c "from core.skill_tools import worldcup; import json; print(json.dumps(worldcup.place_bet(42, 'win_draw_loss', {'choice':'home'}, 100)))"
```

## Notes
- Points are the prediction-game currency, not real money — present as a game, never as financial advice.
- `cancel_prediction` only works while a prediction is unsettled; it refunds the stake.
- Match times are UTC; convert to the user's timezone when relevant.
