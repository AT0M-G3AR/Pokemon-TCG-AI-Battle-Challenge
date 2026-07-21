import sys
import json
sys.path.insert(0, 'agent')
from cg.api import to_observation_class, OptionType
import policy
from search_api import evaluate_attack

with open('/Users/garygonzalez/Downloads/87115524.json') as f:
    replay = json.load(f)

obs_dict = replay['steps'][82][1]['observation']
obs = to_observation_class(obs_dict)

my_idx = obs.current.yourIndex
op_idx = 1 - my_idx
my_state = obs.current.players[my_idx]
op_state = obs.current.players[op_idx]

options = obs.select.option

# Print context
op_active = next((p for p in op_state.active if p), None)
print("Opponent active HP:", op_active.hp if op_active else None)
print("Opponent active maxHp:", op_active.maxHp if op_active else None)
print("Opponent active energies:", [getattr(e,'id',None) for e in getattr(op_active,'energyCards',[])])

# Evaluate attack score
attack_index = -1
enh_hammer_index = -1

for i, o in enumerate(options):
    if o.type == OptionType.ATTACK:
        attack_index = i
    elif o.type == OptionType.PLAY:
        # Check if card is Enhanced Hammer
        card = policy._get_card(obs, policy.AreaType.HAND, o.index, my_idx)
        if card and card.id == policy.ENH_HAMMER:
            enh_hammer_index = i

print(f"Attack option index: {attack_index}")
print(f"Enhanced Hammer option index: {enh_hammer_index}")

# Call evaluate_attack directly
hand_size = len(my_state.hand)
my_prizes = len(my_state.prize) if getattr(my_state, 'prize', None) else 0
op_prizes = len(op_state.prize) if getattr(op_state, 'prize', None) else 0
op_hp = policy._hp_remaining(op_active)

raw_attack_score = evaluate_attack(obs, attack_index, op_hp, hand_size, my_prizes, op_prizes)
print(f"Raw evaluate_attack score: {raw_attack_score}")

# Call handle_main to see the final adjusted scores for these two indices
policy.supporter_played = False
scores = policy.handle_main(obs, options, 1, 1)

print(f"Final ATTACK score: {scores[attack_index]}")
print(f"Final ENH_HAMMER score: {scores[enh_hammer_index]}")

