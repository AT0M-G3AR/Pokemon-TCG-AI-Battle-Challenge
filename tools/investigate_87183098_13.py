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

for p_idx in range(2):
    step = replay['steps'][13]
    obs_dict = step[p_idx].get('observation')
    action_raw = step[p_idx].get('action')
    if not obs_dict or action_raw is None:
        continue
    print(f"\n--- Player {p_idx} ---")
    print(f"Action taken: {action_raw}")
    obs = to_observation_class(obs_dict)
    if obs.select:
        actions = action_raw if isinstance(action_raw, list) else [action_raw]
        for action in actions:
            if action < len(obs.select.option):
                opt = obs.select.option[action]
                print(f"Chosen Action: {action} -> type={opt.type}, index={opt.index}")
                if opt.type == OptionType.PLAY:
                    cid = obs.current.players[obs.current.yourIndex].hand[opt.index].id
                    print(f"  Played from hand: {get_card_name(cid)} (id={cid})")

