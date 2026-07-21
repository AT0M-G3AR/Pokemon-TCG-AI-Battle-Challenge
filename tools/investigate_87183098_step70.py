import sys
import json
import os
sys.path.insert(0, 'agent')
from cg.api import to_observation_class, OptionType, all_card_data

with open('/Users/garygonzalez/Downloads/87183098.json') as f:
    replay = json.load(f)

CARD_DB = {c.cardId: c for c in all_card_data()}
def get_card_name(cid):
    if not cid: return "None"
    return CARD_DB.get(cid).name if cid in CARD_DB else str(cid)

p_idx = 1
for step_idx in [69, 70, 71, 72, 73]:
    step = replay['steps'][step_idx]
    print(f"\n==== STEP {step_idx} ====")
    obs = to_observation_class(step[p_idx].get('observation'))
    my_state = obs.current.players[obs.current.yourIndex]
    
    # Action taken FROM this observation is stored in the NEXT step (if any)
    next_action = None
    if step_idx + 1 < len(replay['steps']):
        next_action = replay['steps'][step_idx+1][p_idx].get('action')
        
    print(f"Action taken from this obs (recorded in step {step_idx+1}): {next_action}")
    if next_action is not None and len(next_action) > 0 and obs.select:
        act_idx = next_action[0]
        if act_idx < len(obs.select.option):
            opt = obs.select.option[act_idx]
            if opt.type == OptionType.ATTACH:
                print(f"  Chosen: Attach to area={opt.inPlayArea} idx={opt.inPlayIndex}")
            elif opt.type == OptionType.CARD:
                print(f"  Chosen: Search/Pick")

    print(f"Context: {obs.select.context if obs.select else 'None'}")
    
    print("Available Options:")
    if obs.select:
        for i, o in enumerate(obs.select.option):
            details = ""
            if o.type == OptionType.ATTACH:
                if o.index < len(my_state.hand):
                    cid = my_state.hand[o.index].id
                    details = f"card={get_card_name(cid)} target: area={o.inPlayArea} idx={o.inPlayIndex}"
            print(f"  {i}: type={o.type} idx={o.index} {details}")
            
    # Print Deck to see if there were Basic Psychic Pokemon
    if obs.select and getattr(obs.select, 'deck', None):
        deck_basics = [get_card_name(c.id) for c in obs.select.deck if 'Basic' in c.subtype and 'Psychic' in c.types]
        print(f"Deck Basic Psychics: {deck_basics}")
    elif step_idx == 71: # let's just print my_state.deck if we can, but we can't.
        pass
