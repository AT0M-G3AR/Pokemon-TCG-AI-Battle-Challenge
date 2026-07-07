import os
import sys
from cg.api import Observation, to_observation_class
from policy import select_action

# ─────────────────────────────────────────────────────────────────────────────
# DECK LOADER — matches Kiyota's exact working format
# deck.csv has NO header row. csv[0] = first card ID.
# Kaggle runtime path: /kaggle_simulations/agent/deck.csv
# ─────────────────────────────────────────────────────────────────────────────

file_path = "deck.csv"
if not os.path.exists(file_path):
    file_path = "/kaggle_simulations/agent/deck.csv"

with open(file_path, "r") as file:
    csv = file.read().split("\n")

my_deck = []
for i in range(60):
    my_deck.append(int(csv[i]))


# ─────────────────────────────────────────────────────────────────────────────
# AGENT ENTRY POINT
# Matches Kiyota's exact interface — proven to work on Kaggle.
# Deck loading happens at module level (not inside agent()),
# which is how the official sample works.
# ─────────────────────────────────────────────────────────────────────────────

def agent(obs_dict: dict) -> list[int]:
    """
    Main agent function called by the cabt simulation engine each turn.

    Returns:
        list[int]: Indices of chosen options, or 60 card IDs on deck selection.
    """
    obs: Observation = to_observation_class(obs_dict)

    # Deck selection phase — obs.select is None at game start
    if obs.select is None:
        return my_deck

    # All other decisions — route through policy
    return select_action(obs)
