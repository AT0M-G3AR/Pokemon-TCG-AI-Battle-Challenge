# v1 — Random Baseline Agent

## Status
✅ Live on ladder — Elo 600.0 (starting score, real games playing overnight)

## What This Is
A legally-compliant baseline agent using Kiyota's public notebook structure
as scaffolding. The policy is random — it picks legal moves at random every turn.
The purpose of v1 is to get on the ladder and establish a baseline Elo score.
Everything from v2 onward is original.

## Scaffolding Credit
The `main.py` module-level deck loading pattern was adapted from Kiyota's
publicly available competition notebook:

> "A Sample Rule-Based Agent Mega Lucario ex Deck"
> https://www.kaggle.com/code/kiyotah/a-sample-rule-based-agent-mega-lucario-ex-deck
> Published publicly on the competition Code tab with Copy & Edit enabled.
> Usage is explicitly permitted under competition Rule 5d (Public Code Sharing).

Specifically, the following pattern was adopted:
- Deck loaded at module level (not inside `agent()`)
- `csv[i]` for `i in range(60)` with no header row in `deck.csv`
- Kaggle runtime path fallback: `/kaggle_simulations/agent/deck.csv`

The deck used in v1 is Kiyota's Mega Lucario ex deck (card IDs from his
public notebook), used as a placeholder to validate the submission pipeline.

## What Is Original
- `policy.py` — 14-context router with full SelectContext scaffold (our own)
- `select_action()` routing architecture
- All handler stubs and v2 TODO annotations
- The `_safe_fallback()` exception safety net

## Architecture
- `main.py` — module-level deck load → `to_observation_class()` → `select_action(obs)`
- `policy.py` — routes by `obs.select.context`, all handlers return random picks
- `deck.csv` — Kiyota's Mega Lucario ex deck (60 card IDs, no header row)

## Deck Used (v1 placeholder)
Kiyota's Mega Lucario ex deck — used solely to validate the submission pipeline.
Will be replaced with our Dragapult EX / Blaziken EX deck in v2.

| Card | Count | ID |
|---|---|---|
| Makuhita | ×2 | 673 |
| Hariyama | ×2 | 674 |
| Lunatone | ×2 | 675 |
| Solrock | ×3 | 676 |
| Riolu | ×3 | 677 |
| Mega Lucario ex | ×4 | 678 |
| Dusk Ball | ×4 | 1102 |
| Switch | ×2 | 1123 |
| Premium Power Pro | ×4 | 1141 |
| Fighting Gong | ×4 | 1142 |
| Poké Pad | ×4 | 1152 |
| Hero's Cape (ACE SPEC) | ×1 | 1159 |
| Boss's Orders | ×2 | 1182 |
| Carmine | ×4 | 1192 |
| Lillie's Determination | ×4 | 1227 |
| Gravity Mountain | ×2 | 1252 |
| Basic Fighting Energy | ×13 | 6 |

## Ladder Results
| Metric | Value |
|---|---|
| Starting Elo | 600.0 |
| Real Elo (after overnight games) | TBD — check morning of July 7 |
| Win Rate | TBD |
| Games Played | TBD |
| Submission Date | July 6, 2026 |
| Commit | 54bf581 |

## Known Weaknesses (all intentional — fixed in v2)
- Policy is entirely random — picks any legal move with equal probability
- No attack scoring (randomly selects including Pass)
- No energy management (attaches to random Pokémon)
- No prize trade awareness
- No bench management logic
- No retreat logic
- Wrong deck for our actual strategy (Dragapult/Blaziken comes in v2)

## What v2 Changes
- Deck: Dragapult EX / Blaziken EX (our real competitive choice)
- Policy: Full heuristic scoring using Kiyota's architecture pattern as reference
- Attack selection: Phantom Dive damage scoring + DAMAGE_COUNTER targeting
- Energy: Psychic energy acceleration logic for Dragapult
- Active selection: Smart replacement after KO
- Search API: Look-ahead for attack evaluation
