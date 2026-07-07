"""
PTCG AI Battle Challenge — Agent Entry Point
AT0M-G3AR | Gary & Team | 2026

Matches the official sample_submission/main.py interface exactly.

KEY FACTS from sample_submission:
  - Uses cg.api.Observation and to_observation_class() — the official typed API
  - obs.select == None → deck selection phase → return read_deck_csv()
  - deck.csv has NO header row — 60 card IDs starting at line 0
  - Kaggle simulation path: /kaggle_simulations/agent/ (note: not /kaggle/simulations/)
  - obs.select.option, obs.select.maxCount, obs.select.minCount are the full API
  - All returned indices must be: >= 0, < len(obs.select.option), no duplicates
"""

import os
import random

from cg.api import Observation, to_observation_class
from policy import select_action


# ─────────────────────────────────────────────────────────────────────────────
# DECK LOADER
# Reads deck.csv — 60 card IDs, one per line, NO header row.
# Matches official sample_submission read_deck_csv() exactly.
# ─────────────────────────────────────────────────────────────────────────────

def read_deck_csv() -> list[int]:
    """
    Load the 60-card deck from deck.csv.

    Format (matches official sample — NO header):
        1158        ← card ID line 0
        721         ← card ID line 1
        ...         ← 60 lines total

    Paths checked in order:
        1. ./deck.csv               (local dev)
        2. /kaggle_simulations/agent/deck.csv  (Kaggle runtime)
    """
    file_path = "deck.csv"
    if not os.path.exists(file_path):
        file_path = "/kaggle_simulations/agent/deck.csv"

    with open(file_path, "r") as file:
        csv = file.read().split("\n")

    # No header — card IDs start at index 0, read exactly 60
    deck = []
    for i in range(60):
        deck.append(int(csv[i]))

    return deck


# ─────────────────────────────────────────────────────────────────────────────
# AGENT ENTRY POINT
# Called every decision step by the cabt engine.
# ─────────────────────────────────────────────────────────────────────────────

def agent(obs_dict: dict) -> list[int]:
    """
    Main agent function — called by the cabt simulation engine each turn.

    Args:
        obs_dict: Raw observation dictionary from the engine.

    Returns:
        list[int]: Indices of chosen options from obs.select.option.
                   Length must be between minCount and maxCount (inclusive).
                   All values >= 0, < len(obs.select.option), no duplicates.
    """
    try:
        obs: Observation = to_observation_class(obs_dict)

        # Deck selection phase — obs.select is None at game start
        if obs.select is None:
            return read_deck_csv()

        # All other decisions — route through policy
        return select_action(obs)

    except Exception as e:
        print(f"[AGENT ERROR] {e} — using safe fallback")
        return _safe_fallback(obs_dict)


def _safe_fallback(obs_dict: dict) -> list[int]:
    """
    Absolute last resort using raw obs_dict (bypasses Observation class).
    Should never be reached in normal play — exists only to prevent forfeits.
    """
    select = obs_dict.get("select")
    if not select:
        return []
    options = select.get("option", [])
    if not options:
        return []
    max_count = select.get("maxCount", 1)
    pick = min(max_count, len(options))
    return random.sample(list(range(len(options))), pick)
