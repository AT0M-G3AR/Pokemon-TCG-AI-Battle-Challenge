#!/bin/bash
# Run this ONCE after cloning your repo locally to create the full folder structure.
# Usage: bash init_repo.sh

echo "Initializing Pokemon-TCG-AI-Battle-Challenge repo structure..."

# Agent folder
mkdir -p agent
touch agent/main.py
touch agent/policy.py
touch agent/deck.csv
cat > agent/build_submission.sh << 'EOF'
#!/bin/bash
# Packages the agent into a submission.tar.gz for Kaggle upload
cd "$(dirname "$0")"
tar -czvf submission.tar.gz main.py policy.py deck.csv
echo "Built submission.tar.gz — upload this to the Kaggle My Submissions tab."
EOF
chmod +x agent/build_submission.sh

# Research folder
mkdir -p research
cat > research/meta_analysis.md << 'EOF'
# Meta Analysis

## Current Ladder Meta (updated as we observe)

| Deck | Estimated Prevalence | Notes |
|---|---|---|
| Crustle | ~50% | Immune to ex/megaEx attacks — must answer with non-ex attackers |
| Bellibolt ex | High | Simple Lightning engine, strong pilot-ability for rule-based agents |
| Alakazam + Dudunsparce | High | Top meta but glass cannon vs Mist Energy counters |
| Typhlosion + Dudunsparce | Medium | Stage-2 combo, complex to pilot cleanly |

## Key Meta Observations
- Crustle's ex immunity makes non-ex attackers essential
- Simple decks outperform complex ones when driven by rule-based agents
- Deck choice dominates agent quality up to a point — then policy quality matters more

## Our Counter-Strategy
*[To be filled in after deck selection]*
EOF

cat > research/deck_theory.md << 'EOF'
# Deck Theory

## Our Deck Choice
*[To be filled in after selection]*

## Why This Deck for AI Piloting
*[Rationale: consistency, linear game plan, minimal branching decisions]*

## Win Condition
*[Primary win condition and how the agent executes it]*

## Matchup Chart
| Opponent | Expected Outcome | Key Considerations |
|---|---|---|
| Crustle | ? | |
| Bellibolt ex | ? | |
| Alakazam | ? | |

## Cards That Require Special Agent Logic
*[List any cards with complex timing or conditional effects]*
EOF

cat > research/card_notes.md << 'EOF'
# Card Interaction Notes

Key cards and interactions the agent policy must explicitly handle.

## Trainer Cards
*[Draw supporters, search cards, energy acceleration — priority order for the agent]*

## Pokémon Abilities
*[Abilities that trigger at specific times — agent must recognize these contexts]*

## Energy Cards
*[Special energy interactions — Enriching Energy, Mist Energy, etc.]*

## Edge Cases
*[Coin flips, status conditions, retreat rules — any non-obvious simulator behavior]*
EOF

# Tools folder
mkdir -p tools/cg-lib
echo "# Place the official cg-lib engine here (download from Kaggle Data tab)" > tools/cg-lib/.gitkeep

# Writeup folder
mkdir -p writeup/assets
cat > writeup/draft.md << 'EOF'
# PTCG AI Battle Challenge — Strategy Report
### Team: AT0M-G3AR | Gary & [Brother]

---

## Overview

This report documents our approach to building a competitive AI Training Agent for the
Pokémon Trading Card Game. Our team brings a unique combination of technical software
engineering experience and deep, hands-on knowledge of the Pokémon TCG — both digitally
and in competitive physical play.

The Pokémon TCG presents a class of AI problem distinct from the perfect-information games
AI has historically conquered. Unlike Chess, Shogi, or Go, where all board state is visible,
PTCG is an imperfect-information game where the opponent's hand, deck order, and prize cards
are all hidden. Combined with probabilistic draw mechanics, coin flip outcomes, and a card pool
of approximately 2,000 cards with deeply interacting effects, no two games unfold the same way.

Our development process is grounded in the same philosophy we apply to all software: build
from real domain knowledge, not just from data. We understand the game as players first,
and we are encoding that understanding into our agent's decision-making policy.

*This report will be updated continuously as our agent develops and our ladder results
accumulate. Final submission is September 13, 2026.*

---

## Deck Concept
*[To be filled in — deck choice, win condition, meta rationale]*

---

## Agent Architecture
*[To be filled in — obs_dict handling, SelectContext scoring, policy design]*

---

## Meta Analysis & Results
*[To be filled in — ladder Elo progression, observed meta, agent adaptations]*

---

## Reflection
*[To be filled in — what worked, what didn't, future directions]*
EOF

# Experiments folder
mkdir -p experiments/v1_random
mkdir -p experiments/v2_heuristic_baseline
mkdir -p experiments/v3_priority_scoring
echo "# v1 — Random agent baseline" > experiments/v1_random/README.md
echo "# v2 — First heuristic policy" > experiments/v2_heuristic_baseline/README.md
echo "# v3 — Per-context priority scoring" > experiments/v3_priority_scoring/README.md

echo ""
echo "✅ Repo structure initialized. Next steps:"
echo "   1. Copy README.md and .gitignore into the root of your repo"
echo "   2. Copy tools/ptcg_setup.py into your tools/ folder"
echo "   3. git add . && git commit -m 'chore: initialize repo structure'"
echo "   4. git push origin main"
