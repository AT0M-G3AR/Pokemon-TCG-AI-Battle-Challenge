# Pokémon TCG AI Battle Challenge
**AT0M-G3AR | Kaggle × The Pokémon Company × HEROZ × Matsuo Institute**

[![Simulation Competition](https://img.shields.io/badge/Kaggle-Simulation%20Track-20BEFF?logo=kaggle)](https://www.kaggle.com/competitions/pokemon-tcg-ai-battle)
[![Strategy Competition](https://img.shields.io/badge/Kaggle-Strategy%20Track-20BEFF?logo=kaggle)](https://www.kaggle.com/competitions/pokemon-tcg-ai-battle-challenge-strategy)

---

## Overview

This repository contains our full submission for the **Pokémon Trading Card Game AI Battle Challenge** — a competition to build an AI Training Agent capable of competing in automated PTCG matches on Kaggle's `cabt` simulation environment.

Our team brings a combination of full-stack software engineering experience and deep, hands-on knowledge of the Pokémon TCG — both digitally and in competitive physical play. Our philosophy: encode real game understanding into the agent's decision-making, not just optimize for the simulator.

> *"AI has faced Chess, Shogi, and Go. Now it takes on the Pokémon Trading Card Game."*
> — The Pokémon Company

---

## Competition Structure

| Track | Description | Deadline |
|---|---|---|
| **Simulation** | AI agent plays automated PTCG matches on a live Elo ladder | Aug 16, 2026 |
| **Strategy** | Written report explaining agent design, deck theory, and meta analysis | Sep 13, 2026 |

Both tracks are required for prize eligibility. The top 8 Strategy finalists each receive **$30,000** and advance to a live tournament in Tokyo.

---

## Repository Structure

```
Pokemon-TCG-AI-Battle-Challenge/
│
├── README.md
├── .gitignore
│
├── agent/                        # Simulation track — submission code
│   ├── main.py                   # Agent entry point: agent(obs_dict) -> list[int]
│   ├── policy.py                 # Decision logic per SelectContext
│   ├── deck.csv                  # 60-card deck (card IDs, one per line)
│   └── build_submission.sh       # Packages agent into submission.tar.gz
│
├── research/                     # Domain knowledge and meta analysis
│   ├── meta_analysis.md          # Current ladder meta — deck archetypes and counters
│   ├── deck_theory.md            # Our deck choice rationale and matchup notes
│   └── card_notes.md             # Key card interactions the agent must handle
│
├── tools/                        # Local development utilities
│   ├── ptcg_setup.py             # Environment setup and obs_dict inspector
│   └── eval.py                   # Head-to-head evaluation vs known meta decks
│
├── writeup/                      # Strategy track — report drafts
│   ├── draft.md                  # Working Kaggle writeup (mirrors the live draft)
│   └── assets/                   # Charts, diagrams, screenshots for media gallery
│
└── experiments/                  # Versioned agent iterations
    ├── v1_random/                # Baseline random agent
    ├── v2_heuristic_baseline/    # First heuristic policy
    └── v3_priority_scoring/      # Scored SelectContext policy
```

---

## Agent Architecture

The agent implements `agent(obs_dict: dict) -> list[int]` — the required interface for the `cabt` environment.

Each call receives:
- `obs_dict["select"]` — the current decision context and list of legal options
- `obs_dict["current"]` — full board state (both players, active/bench Pokémon, hand sizes, prize counts, energy, status conditions)
- `obs_dict["logs"]` — game event log

The agent returns a list of option indices corresponding to the selected legal moves.

**Current approach:** Rule-based heuristic policy with per-`SelectContext` scoring. No crashes guaranteed via `_legal_fallback`.

---

## Local Setup

```bash
# 1. Clone the repo
git clone https://github.com/AT0M-G3AR/Pokemon-TCG-AI-Battle-Challenge.git
cd Pokemon-TCG-AI-Battle-Challenge

# 2. Create virtual environment
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install kaggle-environments==1.30.1

# 4. Download the official cg-lib engine from the Kaggle Data tab
#    Place it at: tools/cg-lib/
#    https://www.kaggle.com/competitions/pokemon-tcg-ai-battle/data

# 5. Run the environment inspector
python tools/ptcg_setup.py
```

---

## Building a Submission

```bash
cd agent
tar -czvf submission.tar.gz main.py policy.py deck.csv
# Upload submission.tar.gz to the Kaggle My Submissions tab
```

Or use the build script:
```bash
bash agent/build_submission.sh
```

---

## Experiment Log

| Version | Agent Type | Deck | Ladder Elo | Notes |
|---|---|---|---|---|
| v1.2 | Random | Kiyota Mega Lucario ex (placeholder) | 179.5 | Baseline established — random policy loses as expected |
| v2 | Heuristic | Dragapult EX / Blaziken EX | TBD | In development |
| v3 | Priority scoring + Search API | Dragapult EX / Blaziken EX | TBD | Planned |

*Updated as ladder results come in.*

---

## Team

| Name | Role |
|---|---|
| Gary (AT0M-G3AR) | Agent architecture, retrieval pipeline, writeup |
| [Brother] | Deck theory, meta analysis, policy logic |

---

## Resources

- [Official Simulation Competition](https://www.kaggle.com/competitions/pokemon-tcg-ai-battle)
- [Official Strategy Competition](https://www.kaggle.com/competitions/pokemon-tcg-ai-battle-challenge-strategy)
- [cabt Engine Documentation](https://matsuoinstitute.github.io/cabt/)
- [Competition Card Data](https://www.kaggle.com/competitions/pokemon-tcg-ai-battle/data)
- [Pokémon TCG Official Rules](https://www.pokemon-card.com/howtoplay/)

---

## License

This repository is released under the **MIT License**. Official competition assets (cg-lib engine, card data, sample notebooks) are subject to The Pokémon Company's competition license and are not redistributed here.
