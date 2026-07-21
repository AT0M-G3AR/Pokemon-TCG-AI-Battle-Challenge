import sys
import time
import json
sys.path.insert(0, 'agent')

# Monkeypatch time.time to simulate a timeout
import shallow_search
original_simulate_forward = shallow_search.simulate_forward

def slow_simulate_forward(*args, **kwargs):
    print("    [Mock] sleeping for 3 seconds to force timeout...")
    time.sleep(3)
    return original_simulate_forward(*args, **kwargs)

shallow_search.simulate_forward = slow_simulate_forward

from cg.api import to_observation_class, OptionType
from shallow_search import shallow_search_pick

with open('/Users/garygonzalez/Downloads/86596187.json') as f:
    replay = json.load(f)

obs_dict = replay['steps'][58][1].get('observation')
obs = to_observation_class(obs_dict)

options = obs.select.option
scores = [float('-inf')] * len(options)
for i, opt in enumerate(options):
    if opt.type == OptionType.PLAY:
        scores[i] = 8000
    elif opt.type == OptionType.EVOLVE:
        scores[i] = 8500
    elif opt.type == OptionType.ATTACK:
        scores[i] = 9000

print("Testing shallow_search_pick with forced timeout...")
try:
    best_idx = shallow_search_pick(obs, options, scores, top_n=3, time_limit_sec=2.0)
    print(f"Test completed. best_idx selected: {best_idx}")
except Exception as e:
    print(f"Exception propagated: {e}")

