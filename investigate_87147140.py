import sys
import json
import os
sys.path.insert(0, 'agent')
from cg.api import to_observation_class, OptionType, SelectContext
import policy

with open('/Users/garygonzalez/Downloads/87147140.json') as f:
    replay = json.load(f)

for step_idx, step in enumerate(replay['steps']):
    if step_idx != 79:
        continue
        
    obs_dict = step[1]['observation']
    obs = to_observation_class(obs_dict)
    
    if obs.select.context == SelectContext.MAIN:
        original_pick_best = policy._pick_best
        policy._pick_best = lambda scores, min_c, max_c, allow_empty=False: scores
        policy.supporter_played = False
        scores = policy.handle_main(obs, obs.select.option, 1, 1)
        policy._pick_best = original_pick_best
        
        my_idx = obs.current.yourIndex
        my_state = obs.current.players[my_idx]
        op_state = obs.current.players[1 - my_idx]
        
        attack_score = -9999.0
        boss_score = -9999.0
        
        for i, opt in enumerate(obs.select.option):
            if opt.type == OptionType.ATTACK:
                attack_score = scores[i]
            elif opt.type == OptionType.PLAY:
                card = policy._get_card(obs, policy.AreaType.HAND, opt.index, my_idx)
                if card and card.id == policy.BOSS_ORDERS:
                    boss_score = max(boss_score, scores[i])
        
        best_score = max(scores)
        best_idx = scores.index(best_score)
        best_opt = obs.select.option[best_idx]
        
        print(f"Step {step_idx} (MAIN):")
        print(f"  ATTACK={attack_score}, BOSS={boss_score}")
        print(f"  Chose Type {best_opt.type} (Score {best_score})")
        if best_opt.type == OptionType.PLAY:
            card = policy._get_card(obs, policy.AreaType.HAND, best_opt.index, my_idx)
            print(f"  Card chosen: {card.id if card else 'None'}")
