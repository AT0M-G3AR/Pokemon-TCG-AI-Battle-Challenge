import sys
import json
import os
sys.path.insert(0, 'agent')
from cg.api import to_observation_class, OptionType
from shallow_search import shallow_search_pick, evaluate_position

with open('/Users/garygonzalez/Downloads/86596187.json') as f:
    replay = json.load(f)

obs_dict = replay['steps'][58][1].get('observation')
obs = to_observation_class(obs_dict)

options = obs.select.option

scores = [float('-inf')] * len(options)
for i, opt in enumerate(options):
    if opt.type == OptionType.PLAY:
        scores[i] = 8000 # Supporter score
    elif opt.type == OptionType.EVOLVE:
        scores[i] = 8500 # Evolve score
    elif opt.type == OptionType.ATTACK:
        scores[i] = 9000 # Attack score

# Patch evaluate_position temporarily to print debug
old_eval = evaluate_position
def new_eval(search_state):
    my_idx = search_state.observation.current.yourIndex
    my_state = search_state.observation.current.players[my_idx]
    opp_state = search_state.observation.current.players[1 - my_idx]
    hand_size = len(my_state.hand) if my_state.hand else 0
    opp_active = next((p for p in opp_state.active if p), None)
    opp_hp_left = opp_active.hp if opp_active else 0
    my_prizes = len([p for p in my_state.prize if p])
    opp_prizes = len([p for p in opp_state.prize if p])
    bench_count = len([p for p in my_state.bench if p])
    
    val = old_eval(search_state)
    print(f"    [Eval] my_prizes={my_prizes} opp_prizes={opp_prizes} opp_hp={opp_hp_left} hand={hand_size} bench={bench_count} -> {val}")
    return val

import shallow_search
shallow_search.evaluate_position = new_eval

best_idx = shallow_search_pick(obs, options, scores, top_n=5)
print(f"Final selected index: {best_idx}")

