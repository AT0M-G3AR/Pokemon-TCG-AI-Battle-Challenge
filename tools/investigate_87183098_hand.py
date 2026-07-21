import sys
import json
import os
sys.path.insert(0, 'agent')
from cg.api import to_observation_class, all_card_data

with open('/Users/garygonzalez/Downloads/87183098.json') as f:
    replay = json.load(f)

CARD_DB = {c.cardId: c for c in all_card_data()}
def get_card_name(cid):
    if not cid: return "None"
    return CARD_DB.get(cid).name if cid in CARD_DB else str(cid)

p_idx = 1
for step_idx in [17, 18, 19]:
    step = replay['steps'][step_idx]
    print(f"\n==== STEP {step_idx} ====")
    obs = to_observation_class(step[p_idx].get('observation'))
    my_state = obs.current.players[obs.current.yourIndex]
    
    hand = [get_card_name(c.id) for c in my_state.hand]
    print(f"Hand: {hand}")
