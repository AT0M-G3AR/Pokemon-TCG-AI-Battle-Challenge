"""
PTCG AI Battle Challenge — v1 Random Baseline Agent
AT0M-G3AR | Gary & Team | 2026

PURPOSE:
    This is the v1 baseline — a legally-compliant random agent that:
      - Never crashes
      - Always returns a valid move
      - Gets you onto the ladder immediately
      - Serves as the benchmark everything else must beat

    Beat this with v2 (heuristic policy in policy.py).

SUBMISSION:
    From the agent/ folder:
        tar -czvf submission.tar.gz main.py policy.py deck.csv
    Upload submission.tar.gz via the Kaggle "Submit Agent" button.
"""

import random
from policy import select_action


def agent(obs_dict: dict) -> list[int]:
    """
    Entry point for the cabt simulation engine.

    Called every time the agent must make a decision.
    Returns a list of option indices from obs_dict["select"]["option"].

    Args:
        obs_dict: {
            "select":  { "context": str, "option": list, "maxCount": int, "minCount": int }
            "current": { "me": PlayerState, "opponent": PlayerState, "turn": int, ... }
            "logs":    [ list of recent game event strings ]
        }

    Returns:
        list[int]: indices of chosen options. Must have length >= minCount.
    """
    try:
        return select_action(obs_dict)
    except Exception as e:
        # Hard fallback — never let the agent crash and forfeit the game
        return _safe_fallback(obs_dict)


def _safe_fallback(obs_dict: dict) -> list[int]:
    """
    Absolute last resort. Returns the minimum legal number of random options.
    This should never be reached in normal play — it exists only as a safety net.
    """
    select = obs_dict.get("select")
    if not select:
        return []

    options = select.get("option", [])
    if not options:
        return []

    min_count = select.get("minCount", 1)
    pick_count = min(min_count, len(options))

    return random.sample(list(range(len(options))), pick_count)
