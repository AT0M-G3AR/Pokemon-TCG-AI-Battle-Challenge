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
    if step_idx < 14 or step_idx > 75:
        continue
    if len(step) < 2: continue
    
    print(f"\n================ STEP {step_idx} ================")
    for p_idx in range(2):
        obs_dict = step[p_idx].get('observation')
        action_raw = step[p_idx].get('action')
        if not obs_dict or action_raw is None:
            continue
            
        print(f"\n--- Player {p_idx} ---")
        print(f"Action taken: {action_raw}")
        
        actions = action_raw if isinstance(action_raw, list) else [action_raw]
        
        obs = to_observation_class(obs_dict)
        state = obs.current
        my_idx = state.yourIndex
        my_state = state.players[my_idx]
        
        if obs.select:
            ctx = obs.select.context
            
            if actions:
                for action in actions:
                    if action < len(obs.select.option):
                        opt = obs.select.option[action]
                        print(f"Chosen Action: {action} -> type={opt.type}, index={opt.index}")
                        if opt.type == OptionType.PLAY:
                            cid = my_state.hand[opt.index].id
                            print(f"  Played from hand: {get_card_name(cid)} (id={cid})")
                        elif opt.type == OptionType.ATTACH:
                            cid = my_state.hand[opt.index].id
                            print(f"  Attached from hand: {get_card_name(cid)} (id={cid})")
                            print(f"  Target: area={opt.inPlayArea}, idx={opt.inPlayIndex}")
                        elif opt.type == OptionType.CARD:
                            target_idx = opt.index
                            if opt.area == 2: # DECK
                                cid = my_state.deck[target_idx].id
                                print(f"  Selected from Deck: {get_card_name(cid)} (id={cid})")
                            elif opt.area == 3: # DISCARD
                                cid = my_state.discard[target_idx].id
                                print(f"  Selected from Discard: {get_card_name(cid)} (id={cid})")
                    else:
                        print(f"Action {action} is out of bounds for options len {len(obs.select.option)}")
                
            print("Available Options:")
            for i, o in enumerate(obs.select.option):
                details = ""
                if o.type == OptionType.PLAY or o.type == OptionType.ATTACH or o.type == OptionType.EVOLVE:
                    if o.index < len(my_state.hand):
                        cid = my_state.hand[o.index].id
                        details = f"card={get_card_name(cid)} (id={cid})"
                elif o.type == OptionType.CARD:
                    if getattr(o, 'area', None) == 2 and o.index < len(my_state.deck):
                        cid = my_state.deck[o.index].id
                        details = f"deck card={get_card_name(cid)} (id={cid})"
                    elif getattr(o, 'area', None) == 3 and o.index < len(my_state.discard):
                        cid = my_state.discard[o.index].id
                        details = f"discard card={get_card_name(cid)} (id={cid})"
                print(f"  {i}: type={o.type} idx={o.index} {details}")
                
        print("My Board:")
        for idx, p in enumerate(my_state.active):
            if p:
                print(f"  Active {idx}: {get_card_name(p.id)}")
        for idx, p in enumerate(my_state.bench):
            if p:
                print(f"  Bench {idx}: {get_card_name(p.id)}")

