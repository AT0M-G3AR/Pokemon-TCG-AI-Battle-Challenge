import sys
import json
sys.path.insert(0, 'agent')
from cg.api import to_observation_class, search_begin, search_step, search_release, OptionType
with open('/Users/garygonzalez/Downloads/86596187.json') as f:
    replay = json.load(f)
obs = to_observation_class(replay['steps'][58][1].get('observation'))
my_state = obs.current.players[obs.current.yourIndex]
my_deck = [p.id for p in my_state.deck] if hasattr(my_state, 'deck') and my_state.deck else [1]*my_state.deckCount
opp_state = obs.current.players[1 - obs.current.yourIndex]
search_state = search_begin(obs, my_deck, [1]*6, [1]*opp_state.deckCount, [1]*6, [1]*opp_state.handCount, [])

s1 = search_step(search_state.searchId, [19]) # Evolve
s2 = search_step(search_state.searchId, [19]) # ATTACK menu
print("Options in s2 (after ATTACK):")
for i, opt in enumerate(s2.observation.select.option):
    print(" ", i, "type:", opt.type, "idx:", opt.index)
search_release(search_state.searchId)
