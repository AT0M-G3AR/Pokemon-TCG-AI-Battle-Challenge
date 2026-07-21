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

options = search_state.observation.select.option
action_idx = -1
for i, opt in enumerate(options):
    if opt.type == OptionType.EVOLVE:
        action_idx = i
        break

if action_idx >= 0:
    print(f"Executing EVOLVE action (index {action_idx})")
    next_state = search_step(search_state.searchId, [action_idx])
    
    new_options = next_state.observation.select.option
    print(f"After EVOLVE, context is {next_state.observation.select.context}")
    print("New options:")
    attack_idx = -1
    for i, opt in enumerate(new_options):
        print(f"  {i}: type={opt.type}")
        if opt.type == OptionType.ATTACK:
            attack_idx = i
            
    if attack_idx >= 0:
        print(f"Chaining ATTACK action (index {attack_idx})")
        final_state = search_step(search_state.searchId, [attack_idx])
        print(f"After ATTACK, context is {final_state.observation.select.context}")
else:
    print("No EVOLVE action found.")

# Clean up
search_release(search_state.searchId)
