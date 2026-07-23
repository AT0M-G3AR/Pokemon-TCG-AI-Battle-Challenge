import json
import sys
import os

sys.path.insert(0, os.path.abspath('agent'))

from policy import select_action
from cg.api import Observation, all_card_data
import msgspec

cards = {c.cardId: c.name for c in all_card_data()}

def test_replay(filename, step_id):
    print(f"\n=== Testing {filename} Step {step_id} ===")
    with open(filename) as f:
        data = json.load(f)
    
    step = data['steps'][step_id]
    entry = step[1]
    obs_dict = entry.get('observation')
    if not obs_dict:
        print("No observation found!")
        return

    # Convert the raw JSON observation into the typed msgspec Observation
    obs = msgspec.json.decode(json.dumps(obs_dict), type=Observation)
    
    # Run our policy
    try:
        action = select_action(obs)
        print(f"Policy Output Action: {action}")
        
        # Resolve what cards this picked
        opts = obs.select.option
        for a in action:
            if a < len(opts):
                opt = opts[a]
                if opt.type.value == 3: # CARD
                    # Get from appropriate area (for TO_DECK, options are from area 3 - discard)
                    player_idx = obs.current.yourIndex
                    area = opt.area.value
                    if area == 3: # Discard
                        c_id = obs.current.players[player_idx].discard[opt.index].id
                        print(f"Selected index {a} -> {cards.get(c_id, c_id)} (ID: {c_id})")
                else:
                    print(f"Selected option {a}: {opt}")
    except Exception as e:
        print(f"Error running policy: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_replay('86596187.json', 90)
    test_replay('86518325.json', 143)

