import sys
import json
import ctypes
sys.path.insert(0, 'agent')
from cg.sim import lib
from cg.api import to_observation_class, OptionType

with open('/Users/garygonzalez/Downloads/86596187.json') as f:
    replay = json.load(f)

# Find a step where we have a supporter or evolve option
obs_dict = None
for p_idx in [0, 1]:
    obs_dict = replay['steps'][58][p_idx].get('observation')
    obs = to_observation_class(obs_dict)
    if obs.select and obs.select.option:
        break

search_input = obs_dict.get("search_begin_input", "")
if search_input:
    search_input_bytes = search_input.encode('ascii')
    search_data = lib.SearchBegin(search_input_bytes)
    search_json = json.loads(search_data.decode())
    search_id = search_json.get("searchId")
    
    print(f"Initial options count: {len(obs.select.option)}")
    # Find a non-turn-ending action (e.g., PLAY supporter or EVOLVE)
    action_idx = -1
    for i, opt in enumerate(obs.select.option):
        if opt.type == OptionType.PLAY or opt.type == OptionType.EVOLVE:
            action_idx = i
            break
            
    if action_idx >= 0:
        print(f"Executing action index {action_idx} (type {obs.select.option[action_idx].type})")
        action_array = (ctypes.c_int * 1)(action_idx)
        result_data = lib.SearchStep(search_id, action_array, 1)
        result_json = json.loads(result_data.decode())
        new_obs = to_observation_class(result_json)
        print(f"After action 1, options count: {len(new_obs.select.option)}")
        
        # Now try a second action
        if len(new_obs.select.option) > 0:
            print("Chaining second action: index 0")
            action_array2 = (ctypes.c_int * 1)(0)
            result_data2 = lib.SearchStep(search_id, action_array2, 1)
            result_json2 = json.loads(result_data2.decode())
            new_obs2 = to_observation_class(result_json2)
            print("Second action successful")
    
    lib.SearchEnd()
