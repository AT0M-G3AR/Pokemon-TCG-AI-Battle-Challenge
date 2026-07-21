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

for step_idx, step in enumerate(replay['steps']):
    if step_idx not in [18, 19]: continue
    if len(step) < 2: continue
    
    p_idx = 1
    obs_dict = step[p_idx].get('observation')
    action_raw = step[p_idx].get('action')
    
    obs = to_observation_class(obs_dict)
    state = obs.current
    my_idx = state.yourIndex
    my_state = state.players[my_idx]
    
    print(f"\n================ STEP {step_idx} Player {p_idx} ================")
    print(f"Action taken: {action_raw}")
    if obs.select:
        actions = action_raw if isinstance(action_raw, list) else [action_raw] if action_raw is not None else []
        for action in actions:
            if action < len(obs.select.option):
                opt = obs.select.option[action]
                print(f"Chosen Action: {action} -> type={opt.type}, index={opt.index}")
                if opt.type == OptionType.ATTACH:
                    cid = my_state.hand[opt.index].id
                    print(f"  Target: area={opt.inPlayArea}, idx={opt.inPlayIndex}")
                
        print("Available Options:")
        for i, o in enumerate(obs.select.option):
            details = ""
            if o.type == OptionType.PLAY or o.type == OptionType.ATTACH or o.type == OptionType.EVOLVE:
                if o.index < len(my_state.hand):
                    cid = my_state.hand[o.index].id
                    details = f"card={get_card_name(cid)} (id={cid})"
            if o.type == OptionType.ATTACH:
                details += f" target: area={o.inPlayArea} idx={o.inPlayIndex}"
            print(f"  {i}: type={o.type} idx={o.index} {details}")
            
    print("My Board:")
    for idx, p in enumerate(my_state.active):
        if p:
            print(f"  Active {idx}: {get_card_name(p.id)} (hp={p.hp})")
    for idx, p in enumerate(my_state.bench):
        if p:
            print(f"  Bench {idx}: {get_card_name(p.id)} (hp={p.hp})")

