# v1 — Random Baseline Agent

## What This Is
A legally-compliant random agent. Never crashes, always returns a valid move.

## Purpose
- Gets us on the ladder immediately with a real Elo score
- Establishes the baseline every future version must beat
- Validates the submission pipeline end-to-end

## Architecture
- `main.py` — entry point, calls `select_action()`, catches all exceptions
- `policy.py` — routes by SelectContext, all handlers return random picks
- `deck.csv` — placeholder deck (update with real card IDs before submitting)

## Ladder Result
| Metric | Value |
|---|---|
| Elo | TBD |
| Win Rate | TBD |
| Games Played | TBD |
| Submission Date | TBD |

## Known Weaknesses (all intentional — fixed in v2)
- No attack scoring (picks randomly, including Pass)
- No energy management (attaches to random Pokémon)
- No prize trade awareness
- No bench management logic
- No retreat logic
