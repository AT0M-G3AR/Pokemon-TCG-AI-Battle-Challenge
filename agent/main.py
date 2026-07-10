import os
import random
from cg.api import Observation, to_observation_class
from policy import select_action

# Load deck — use the same approach as Kiyota's working submission
# __file__ is NOT available in Kaggle's exec() environment
file_path = "deck.csv"
if not os.path.exists(file_path):
    file_path = "agent/deck.csv"
if not os.path.exists(file_path):
    file_path = "/kaggle_simulations/agent/deck.csv"

with open(file_path, "r") as file:
    csv = file.read().split("\n")

my_deck = []
for i in range(60):
    my_deck.append(int(csv[i]))


def agent(obs_dict: dict) -> list[int]:
    try:
        obs: Observation = to_observation_class(obs_dict)
        if obs.select is None:
            return my_deck
        return select_action(obs)
    except Exception as e:
        print(f"[AGENT ERROR] {e}")
        select = obs_dict.get("select")
        if not select:
            return []
        options = select.get("option", [])
        if not options:
            return []
        return [0]
