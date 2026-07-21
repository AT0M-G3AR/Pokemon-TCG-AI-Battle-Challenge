import sys
import json
sys.path.insert(0, 'agent')
from cg.api import to_observation_class, OptionType
import policy

with open('86685694.json') as f:
    replay = json.load(f)

obs_dict = replay['steps'][34][1]['observation']
obs = to_observation_class(obs_dict)

my_idx = obs.current.yourIndex
op_idx = 1 - my_idx

from cg.api import Card
lana_aid = Card(id=1184, playerIndex=my_idx, serial=999)
obs.current.players[my_idx].hand = [lana_aid] * 2

if obs.current.players[op_idx].active:
    obs.current.players[op_idx].active[0].hp = 300
    obs.current.players[op_idx].active[0].maxHp = 300

# Put some high and low value pieces in discard
abra = Card(id=741, playerIndex=my_idx, serial=998)
psychic = Card(id=5, playerIndex=my_idx, serial=997)
obs.current.players[my_idx].discard = [abra, psychic]

obs.select.context = 1
class MockOption:
    def __init__(self):
        self.type = OptionType.PLAY
        self.index = 0

obs.select.options = [MockOption()]
policy.supporter_played = False
scores = policy.handle_main(obs, obs.select.options, 1, 1)
print("Option 0 score (should be 8500.0):", scores[0])
