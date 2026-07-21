import sys
import json
import os
sys.path.insert(0, 'agent')
from cg.api import to_observation_class, OptionType, SelectContext, all_card_data

with open('/Users/garygonzalez/Downloads/87183098.json') as f:
    replay = json.load(f)

CARD_DB = {c.cardId: c for c in all_card_data()}
def get_card_name(cid):
    if not cid: return "None"
    return CARD_DB.get(cid).name if cid in CARD_DB else str(cid)

p_idx = 1
for step_idx in [17, 18, 19, 20, 21]:
    step = replay['steps'][step_idx]
    action_raw = step[p_idx].get('action')
    print(f"\n==== STEP {step_idx} Player {p_idx} ====")
    print(f"Action IN THIS STEP: {action_raw}")
    
    obs = to_observation_class(step[p_idx].get('observation'))
    my_state = obs.current.players[obs.current.yourIndex]
    
    print("My Active:")
    for idx, p in enumerate(my_state.active):
        if p:
            energies = [get_card_name(e.id) for e in p.energyCards]
            print(f"  Active {idx}: {get_card_name(p.id)} - energies: {energies}")
            
    print("My Bench:")
    for idx, p in enumerate(my_state.bench):
        if p:
            energies = [get_card_name(e.id) for e in p.energyCards]
            print(f"  Bench {idx}: {get_card_name(p.id)} - energies: {energies}")

