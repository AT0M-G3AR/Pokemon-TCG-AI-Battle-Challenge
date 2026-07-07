import os
import random
from cg.api import Observation, to_observation_class
from policy import select_action

def read_deck_csv() -> list[int]:
    # Try every possible path Kaggle might use
    candidates = [
        "deck.csv",
        "/kaggle_simulations/agent/deck.csv",
        "/kaggle/simulations/agent/deck.csv",
        os.path.join(os.path.dirname(__file__), "deck.csv"),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "deck.csv"),
    ]

    csv_lines = None
    for path in candidates:
        try:
            with open(path, "r") as f:
                content = f.read().strip()
                csv_lines = [line.strip() for line in content.split("\n") if line.strip()]
                print(f"[deck] Loaded from: {path} ({len(csv_lines)} lines)")
                break
        except Exception:
            continue

    if csv_lines is None:
        print("[deck] ERROR: deck.csv not found in any path")
        return []

    # Parse card IDs — skip header row if present
    deck = []
    for line in csv_lines:
        if line.lower() == "deck":
            continue  # skip header
        try:
            deck.append(int(line))
        except ValueError:
            continue  # skip any blank or malformed lines

    print(f"[deck] Parsed {len(deck)} card IDs")
    return deck


def agent(obs_dict: dict) -> list[int]:
    try:
        obs: Observation = to_observation_class(obs_dict)
        if obs.select is None:
            deck = read_deck_csv()
            print(f"[agent] Returning deck of {len(deck)} cards")
            return deck
        return select_action(obs)
    except Exception as e:
        print(f"[AGENT ERROR] {e}")
        return _safe_fallback(obs_dict)


def _safe_fallback(obs_dict: dict) -> list[int]:
    select = obs_dict.get("select")
    if not select:
        return []
    options = select.get("option", [])
    if not options:
        return []
    max_count = select.get("maxCount", 1)
    pick = min(max_count, len(options))
    return random.sample(list(range(len(options))), pick)
