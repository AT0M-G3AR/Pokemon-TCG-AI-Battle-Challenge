# PTCG AI Battle Challenge — Team Onboarding Guide
## For: [Brother's Name] | AT0M-G3AR Team | July 2026

---

## What This Competition Is

We are entered in **The Pokémon Company PTCG AI Battle Challenge** on Kaggle — a competition
to build an AI agent that plays the Pokémon Trading Card Game autonomously.

There are two tracks we are competing in simultaneously:

**Simulation Track** (deadline: August 16, 2026)
- Submit an AI agent that plays PTCG matches on Kaggle's ladder
- Scored by Elo rating — more wins = higher Elo
- Top agents qualify for the Strategy prize

**Strategy Track** (deadline: September 13, 2026)
- A 2,000-word written report explaining our agent design, deck choice, and results
- 70% of score is "Model Approach" — how well we explain our AI strategy
- 20% is "Deck Concept" — why we chose this deck
- 10% is "Report Quality"
- Top 8 teams each receive **$30,000** and advance to a live tournament in Tokyo

**Prize pool: $290,000+**

---

## Our Current Status

| Item | Status |
|---|---|
| Both competitions registered | ✅ |
| GitHub repo live | ✅ `github.com/AT0M-G3AR/Pokemon-TCG-AI-Battle-Challenge` |
| Strategy writeup draft saved on Kaggle | ✅ |
| v1 agent submitted (random baseline) | ✅ Elo: 189.2 |
| v2.0 agent submitted (first heuristic) | ✅ Elo: 386.9 |
| v2.1 agent submitted (context fixes) | ⏳ Pending result |
| v3 (Search API + tuned policy) | 🔲 Not started |

---

## Our Deck — Dragapult ex / Blaziken ex

This is the deck we play on TCG Live. It has been verified as 60 legal cards.

### How the Deck Wins
Dragapult ex is the primary attacker. It needs **1 Psychic Energy + 1 Fire Energy**
to use **Phantom Dive**: deals 200 damage to the opponent's Active Pokémon, plus
60 damage spread across the opponent's Bench (you decide how to split the 60).

Blaziken ex is the support engine — its Ability attaches 2 Fire Energy from the
discard pile to your Pokémon once per turn. This fuels Dragapult ex's Fire requirement.

The goal is to set up Dragapult ex by turn 3 and use Phantom Dive every turn,
chaining KOs while the bench spread damage sets up future prizes.

### Full Deck List

| Card | Count | Card ID | Role |
|---|---|---|---|
| Dreepy | 4 | 119 | Dragapult evolution base |
| Drakloak | 3 | 120 | Dragapult stage 1 |
| Dragapult ex | 3 | 121 | Primary attacker |
| Torchic | 2 | 324 | Blaziken evolution base |
| Combusken | 1 | 325 | Blaziken stage 1 |
| Blaziken ex | 2 | 326 | Energy acceleration engine |
| Buddy-Buddy Poffin | 4 | 1086 | Search 2 Basics ≤70 HP → bench |
| Night Stretcher | 2 | 1097 | Recover Pokémon + energy from discard |
| Poké Pad | 3 | 1152 | Search non-Rule Box Pokémon → hand |
| Rare Candy | 3 | 1079 | Dreepy → Dragapult ex (skip Drakloak) |
| Switch | 2 | 1123 | Swap active with bench |
| Ultra Ball | 4 | 1121 | Discard 2, search any Pokémon |
| Unfair Stamp | 1 | 1080 | Opponent shuffles hand to 2 cards |
| Risky Ruins | 1 | 1260 | Stadium |
| Team Rocket's Watchtower | 1 | 1256 | Stadium |
| Boss's Orders | 2 | 1182 | Pull opponent's benched Pokémon to active |
| Colress's Tenacity | 2 | 1194 | Search Stadium + Energy → hand |
| Crispin | 2 | 1198 | Search 2 different Basic Energy from deck; attach 1, put 1 in hand |
| Dawn | 2 | 1231 | Search Basic + Stage 1 + Stage 2 → hand |
| Lillie's Determination | 4 | 1227 | Shuffle hand, draw 6 (draw 8 if 6 prizes left) |
| Basic Psychic Energy | 6 | 5 | Dragapult ex energy |
| Basic Fire Energy | 6 | 2 | Blaziken ex / Dragapult ex energy |

---

## Repository Structure

```
Pokemon-TCG-AI-Battle-Challenge/
├── agent/
│   ├── main.py          ← Agent entry point (do not change structure)
│   ├── policy.py        ← ALL the AI decision logic lives here
│   ├── deck.csv         ← 60 card IDs, one per line, NO header row
│   ├── build_submission.sh  ← Run this to package the submission
│   └── cg/              ← Simulation engine (do not modify)
├── experiments/
│   ├── v1_random/       ← Baseline random agent docs
│   ├── v2_heuristic_baseline/  ← Current agent docs
│   └── v3_priority_scoring/    ← Next version placeholder
├── research/
│   ├── deck_theory.md   ← Deck strategy documentation
│   ├── meta_analysis.md ← Ladder meta observations
│   └── card_notes.md    ← Key card interaction notes
├── tools/
│   └── kaggle_cli_workflow.sh  ← CLI commands for managing submissions
└── writeup/
    └── draft.md         ← Strategy competition writeup (update as we build)
```

---

## How to Set Up Your Local Environment

```bash
# 1. Clone the repo
git clone https://github.com/AT0M-G3AR/Pokemon-TCG-AI-Battle-Challenge.git
cd Pokemon-TCG-AI-Battle-Challenge

# 2. Create virtual environment (use Python 3.11 specifically)
python3.11 -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install kaggle-environments==1.30.1

# 4. Fix macOS Gatekeeper issue (Mac only — required to run locally)
xattr -d com.apple.quarantine agent/cg/libcg.dylib 2>/dev/null || true
codesign --force --sign - agent/cg/libcg.dylib

# 5. Verify the environment works
cd agent
python3.11 -c "
from cg.api import Observation, to_observation_class, all_card_data
cards = all_card_data()
print(f'Engine loaded. {len(cards)} cards available.')
"
```

---

## How to Run a Local Test Game

```bash
cd /path/to/Pokemon-TCG-AI-Battle-Challenge
source venv/bin/activate

python3.11 - << 'EOF'
import sys
sys.path.insert(0, 'agent')
from kaggle_environments import make
from main import agent

env = make("cabt")
env.run([agent, agent])

with open("replay.html", "w") as f:
    f.write(env.render(mode="html"))
print("Done — serve with: python3 -m http.server 8080")
print("Then open: http://localhost:8080/replay.html")
EOF

# View the replay
python3 -m http.server 8080
# Open http://localhost:8080/replay.html in your browser
```

---

## How to Build and Submit to Kaggle

```bash
# Step 1 — Build the submission package
cd /path/to/Pokemon-TCG-AI-Battle-Challenge/agent
bash build_submission.sh
# This creates submission.tar.gz — clean, no __pycache__

# Step 2 — Upload to Kaggle
# Go to: kaggle.com/competitions/pokemon-tcg-ai-battle/submissions
# Click: Submit Agent
# Upload: agent/submission.tar.gz
# Description: write what version and what changed (e.g. "v2.1: fix ATTACH_TO context")
# Click: Submit

# You have 5 submissions per day. They reset daily.
# Only your 2 most recent submissions are active on the ladder.
# Check your Elo score on the Submissions tab after ~30 minutes.
```

---

## How the Agent Makes Decisions (policy.py)

The agent receives an observation every time it needs to make a decision.
The observation includes the full board state and a list of legal options.
The agent must return a list of option indices — which options to choose.

`main.py` handles the top-level routing:
- If `obs.select is None` → deck selection phase → return the 60 card IDs from deck.csv
- Otherwise → call `select_action(obs)` from policy.py

`policy.py` routes by `SelectContext` (the type of decision being made):

| Context | Value | What It Is |
|---|---|---|
| MAIN | 0 | Main turn — play cards, attack, retreat |
| SETUP_ACTIVE_POKEMON | 1 | Choose starter Pokémon |
| SETUP_BENCH_POKEMON | 2 | Fill bench during setup |
| TO_BENCH | 5 | Place a Pokémon onto bench mid-game |
| TO_HAND | 7 | Choose card(s) to take into hand from search |
| DISCARD | 8 | Choose cards to discard (e.g. Ultra Ball cost) |
| DAMAGE_COUNTER | 13 | Phantom Dive — choose bench targets for spread damage |
| ATTACH_FROM | 21 | Choose which energy to attach from hand |
| ATTACH_TO | 22 | Choose which Pokémon to attach the energy to |
| DISCARD_ENERGY | 30 | Choose energy to discard |
| EVOLVE | 37 | Choose which in-play Pokémon to evolve |
| ACTIVATE | 43 | Ability yes/no (Blaziken ex ability) |

Each handler scores every legal option and returns the best choice(s).

---

## How to Change the Policy Logic

All logic lives in `agent/policy.py`. Find the handler for the decision type
you want to improve and edit the scoring:

### Example: Change which card gets priority in hand search (TO_HAND)

Find `handle_to_hand()` in policy.py. The scores dict controls priority:
```python
if cid == DRAGAPULT_EX:
    score = 9000.0   # ← increase this number to prioritize Dragapult ex more
elif cid == RARE_CANDY:
    score = 7500.0   # ← decrease to deprioritize Rare Candy in search
```
Higher score = agent prefers this option. Score below -9000 = never pick this.

### Example: Change attack priority

Find `handle_main()` and look for `o.type == OptionType.ATTACK`:
```python
if active and _dragapult_ready(active):
    score = 9000.0   # ← Phantom Dive priority
```

### Example: Change bench damage targeting

Find `handle_damage_counter()`. This controls where Phantom Dive's 60
spread damage goes. Currently targets highest-prize Pokémon closest to KO.

### After any change:
```bash
cd agent
bash build_submission.sh
# Upload submission.tar.gz to Kaggle
```

---

## How to Change the Deck

Edit `agent/deck.csv` — one card ID per line, exactly 60 lines, NO header row.

To find a card's ID, search `EN_Card_Data.csv` (in the Kaggle Data tab):
```bash
python3.11 -c "
import csv
with open('/path/to/EN_Card_Data.csv') as f:
    for row in csv.DictReader(f):
        if 'CardName' in row.get('Card Name', ''):
            print(row.get('Card ID'), row.get('Card Name'))
"
```

After changing `deck.csv`, also update the card ID constants at the top of
`policy.py` if you add new cards, so the policy knows how to handle them.

---

## Current Known Issues / Things to Improve

### High Priority (most Elo impact)
1. **ACTIVATE context (43)** — Blaziken ex ability activation not yet handled explicitly.
   Currently falls to generic random. Should always say YES when Fire energy in discard.

2. **DAMAGE_COUNTER_COUNT context (39)** — May control how Phantom Dive's 60 damage
   is split. Not yet handled. Need to verify in game logs.

3. **TO_HAND_ENERGY context (31)** — Crispin puts one energy in hand after attaching
   the other. Need to ensure we pick the right one for hand vs attachment.

4. **Supporter priority tuning** — The order in which we play Supporters each turn
   affects what we can do. Dawn vs Lillie's Determination vs Crispin vs Boss's Orders
   timing needs real-game testing.

### Medium Priority
5. **Prize trade awareness** — Agent doesn't track whether it's ahead or behind on prizes.
   Unfair Stamp should only be played when we're behind (fewer prizes taken).

6. **Boss's Orders timing** — Should factor in whether Dragapult ex is ready to attack
   that same turn (no point pulling a bench target if we can't attack).

7. **Rare Candy sequencing** — Agent should play Rare Candy before playing Supporters
   that might shuffle hand (don't want to discard the Dragapult ex).

### Low Priority (v3 targets)
8. **Search API look-ahead** — The engine provides a Search API that lets us simulate
   game outcomes before committing. Using this for attack and bench-targeting decisions
   could add +200 Elo.

9. **Meta counter-strategy** — Track what deck the opponent is running based on their
   Pokémon and adjust Phantom Dive targeting accordingly.

---

## Key Files to Read

Before making changes, read these to understand the full context:

- `research/deck_theory.md` — Full deck strategy and agent priority rules
- `experiments/v2_heuristic_baseline/README.md` — What v2 does and its limitations
- `writeup/draft.md` — Strategy competition writeup in progress

---

## Kaggle CLI Commands (useful for monitoring)

```bash
# Install
pip install kaggle
# Put kaggle.json at ~/.kaggle/kaggle.json (get from kaggle.com/settings/api)

# Check your submissions and Elo
kaggle competitions submissions pokemon-tcg-ai-battle

# Check the leaderboard
kaggle competitions leaderboard pokemon-tcg-ai-battle -s

# Download episode replays for debugging
kaggle competitions episodes YOUR_SUBMISSION_ID
kaggle competitions replay EPISODE_ID -p ./replays/
```

---

## Competition Deadlines

| Date | Milestone |
|---|---|
| **August 9, 2026** | Team merger deadline — must be on same Kaggle team |
| **August 9, 2026** | Simulation entry deadline |
| **August 16, 2026** | Final Simulation submission |
| **September 13, 2026 @ 7:59 PM EDT** | Strategy writeup deadline — hit SUBMIT not just Save Draft |

---

## One Most Important Thing

The agent needs to use Phantom Dive (Dragapult ex's attack) every single turn
once it has 1 Psychic + 1 Fire attached. Every decision in `policy.py` should
be evaluated by asking: "Does this help us get Dragapult ex attacking faster?"

Your TCG knowledge is the biggest edge we have. If you see the agent making a
decision you would never make as a player, find the handler for that context
in `policy.py` and fix the scoring. Every improvement you make can be tested
locally with `replay.html` and verified on the real ladder within 30 minutes.
