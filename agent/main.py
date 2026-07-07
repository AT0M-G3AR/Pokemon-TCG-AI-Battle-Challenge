import os
import random

from cg.api import Observation, to_observation_class
from policy import select_action

def read_deck_csv() -> list[int]:
    """Read deck.csv.
    
    Returns:
        list[int]: A list of card IDs in the deck.
    """
    file_path = "deck.csv"
    if not os.path.exists(file_path):
        file_path = "/kaggle_simulations/agent/" + file_path
    with open(file_path, "r") as file:
        csv = file.read().split("\n")
    deck = []
    for i in range(60):
        deck.append(int(csv[i]))
    return deck

def agent(obs_dict: dict) -> list[int]:
    """Implement Your Pokémon Trading Card Game Agent.

    Each element in the returned list must be >= 0 and < len(obs.select.option).
    The list length must be between obs.select.minCount and obs.select.maxCount (inclusive), with no duplicate elements.
    
    Returns:
        list[int]: A list of option index.
    """
    try:
        obs: Observation = to_observation_class(obs_dict)
        if obs.select == None:
            # In the initial selection, the obs.select is None, and it is necessary to return the deck.
            # The deck is a list of 60 card IDs.
            # The deck must comply with the Pokémon Trading Card Game rules.
            return read_deck_csv()
        
        return select_action(obs)
    except Exception as e:
        print(f"[AGENT ERROR] {e} — using safe fallback")
        # Safe fallback matching Kiyota's random.sample exactly
        select = obs_dict.get("select")
        if not select:
            return []
        options = select.get("option", [])
        if not options:
            return []
        max_count = select.get("maxCount", 1)
        pick = min(max_count, len(options))
        return random.sample(list(range(len(options))), pick)
