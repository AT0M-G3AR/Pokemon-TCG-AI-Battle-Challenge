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

best_idx = shallow_search_pick(obs, options, scores, top_n=6)
print(f"Final selected index: {best_idx}")

