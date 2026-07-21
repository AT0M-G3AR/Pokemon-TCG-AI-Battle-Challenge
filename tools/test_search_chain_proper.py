import sys
import json
import os
sys.path.insert(0, 'agent')
from cg.api import to_observation_class, search_begin, search_step, search_release, OptionType

with open('/Users/garygonzalez/Downloads/86596187.json') as f:
    replay = json.load(f)

# Find step 58
obs_dict = replay['steps'][58][1].get('observation')
obs = to_observation_class(obs_dict)

my_state = obs.current.players[obs.current.yourIndex]
opp_state = obs.current.players[1 - obs.current.yourIndex]

# Dummy predictions for initialization
my_deck = [p.id for p in my_state.deck] if hasattr(my_state, 'deck') and my_state.deck else [1]*obs.current.players[obs.current.yourIndex].deckCount
my_prize = [1]*6
opp_deck = [1]*opp_state.deckCount
opp_prize = [1]*6
opp_hand = [1]*opp_state.handCount
opp_active = []
if opp_state.active and opp_state.active[0] is None:
    opp_active = [1] # dummy card ID

# Initialize search
search_state = search_begin(obs, my_deck, my_prize, opp_deck, opp_prize, opp_hand, opp_active)
print(f"Search started with ID: {search_state.searchId}")

options = search_state.observation.select.option
action_idx = -1
for i, opt in enumerate(options):
    if opt.type == OptionType.PLAY:
        action_idx = i
        break

if action_idx >= 0:
    print(f"Executing action 1 (index {action_idx})")
    next_state = search_step(search_state.searchId, [action_idx])
    
    new_options = next_state.observation.select.option
    print(f"After action 1, options count: {len(new_options)}")
    
    if len(new_options) > 0:
        print(f"Executing action 2 (index 0)")
        final_state = search_step(search_state.searchId, [0])
        print(f"After action 2, options count: {len(final_state.observation.select.option)}")

# Clean up
search_release(search_state.searchId)
