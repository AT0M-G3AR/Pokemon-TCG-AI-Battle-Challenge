import sys
import json
sys.path.insert(0, 'agent')
from cg.api import to_observation_class, OptionType, Card
import policy
from search_api import evaluate_attack

# Patch _pick_best to return raw scores instead of indices for our test
policy._pick_best = lambda scores, min_c, max_c, allow_empty=False: scores

def load_replay_step_82():
    with open('/Users/garygonzalez/Downloads/87115524.json') as f:
        replay = json.load(f)
    obs_dict = replay['steps'][82][1]['observation']
    return to_observation_class(obs_dict)

def get_indices(options, obs, my_idx):
    attack_index = -1
    enh_hammer_index = -1
    for i, o in enumerate(options):
        if o.type == OptionType.ATTACK:
            attack_index = i
        elif o.type == OptionType.PLAY:
            card = policy._get_card(obs, policy.AreaType.HAND, o.index, my_idx)
            if card and card.id == policy.ENH_HAMMER:
                enh_hammer_index = i
    return attack_index, enh_hammer_index

print("--- TEST 1: Replay Step 82 (Mist Energy Active on Crustle) ---")
obs1 = load_replay_step_82()
my_idx = obs1.current.yourIndex
op_idx = 1 - my_idx
attack_idx1, enh_idx1 = get_indices(obs1.select.option, obs1, my_idx)

policy.supporter_played = False
scores1 = policy.handle_main(obs1, obs1.select.option, 1, 1)
print(f"ATTACK score: {scores1[attack_idx1]}")
print(f"ENH_HAMMER score: {scores1[enh_idx1]}")


print("\n--- TEST 2: Regression (Normal Attack, No Mist Energy) ---")
obs2 = load_replay_step_82()
op_active2 = next((p for p in obs2.current.players[op_idx].active if p), None)
# Remove Mist Energy
op_active2.energyCards = [e for e in op_active2.energyCards if e.id != 11]

attack_idx2, enh_idx2 = get_indices(obs2.select.option, obs2, my_idx)
policy.supporter_played = False
scores2 = policy.handle_main(obs2, obs2.select.option, 1, 1)
print(f"ATTACK score: {scores2[attack_idx2]}")
print(f"ENH_HAMMER score: {scores2[enh_idx2]}")


print("\n--- TEST 3: Clefairy ex Attacking into Mist Energy ---")
obs3 = load_replay_step_82()
# Make our active Pokemon Clefairy ex (id 1459, LILLIE_CLEFAIRY_EX = 1459)
my_active3 = next((p for p in obs3.current.players[my_idx].active if p), None)
my_active3.id = 1459

attack_idx3, enh_idx3 = get_indices(obs3.select.option, obs3, my_idx)
policy.supporter_played = False
scores3 = policy.handle_main(obs3, obs3.select.option, 1, 1)
print(f"ATTACK score: {scores3[attack_idx3]}")
print(f"ENH_HAMMER score: {scores3[enh_idx3]}")
