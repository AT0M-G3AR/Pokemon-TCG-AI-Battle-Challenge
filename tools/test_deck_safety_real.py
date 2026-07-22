import sys, os
sys.path.insert(0, os.path.abspath('agent'))
from kaggle_environments import make

env = make("cabt")
obs_list = env.reset()
raw_obs = obs_list[0].observation

import policy
from cg.api import to_observation_class, OptionType, SelectContext, AreaType
from policy import POKE_PAD, HILDA, DAWN, POFFIN, DUDUNSPARCE, KADABRA, TELEPATH_ENERGY, ENRICHING_ENERGY

obs = to_observation_class(raw_obs)
my_idx = obs.current.yourIndex

# Spy on the helper
eval_log = []
def spy_deck_safety(deck_count, draw_amount):
    disc = policy._deck_safety_discount_orig(deck_count, draw_amount)
    eval_log.append((deck_count, draw_amount, disc))
    return disc
policy._deck_safety_discount_orig = policy._deck_safety_discount
policy._deck_safety_discount = spy_deck_safety
policy._pick_best = lambda scores, min_c, max_c: scores

# We need to mock _get_card because we will pass fake options
policy._get_card = lambda o, area, index, my_idx: type('obj', (), {'id': index, 'skills': [], 'energies': []})

def run_scenario(name, deck_counts, fn):
    print(f"\n--- {name} ---")
    for dc in deck_counts:
        eval_log.clear()
        obs.current.players[my_idx].deckCount = dc
        try:
            scores = fn(obs)
            if eval_log:
                print(f"Deck={dc:2} -> draw={eval_log[0][1]}, penalty applied={eval_log[0][2]:.1f}, raw scores={scores}")
            else:
                print(f"Deck={dc:2} -> (No safety evaluation), raw scores={scores}")
        except Exception as e:
            print(f"Deck={dc:2} -> Error: {e}")

counts = [40, 3, 1, 0]
opt_play = lambda cid: type('obj', (), {'type': OptionType.PLAY, 'area': AreaType.HAND, 'index': cid})
opt_act = lambda t, cid: type('obj', (), {'type': t, 'area': AreaType.BENCH, 'index': cid})

run_scenario("Poké Pad", counts, lambda o: policy.handle_main(o, [opt_play(POKE_PAD)], 0, 1))
run_scenario("Hilda", counts, lambda o: policy.handle_main(o, [opt_play(HILDA)], 0, 1))
run_scenario("Dawn", counts, lambda o: policy.handle_main(o, [opt_play(DAWN)], 0, 1))
run_scenario("Buddy-Buddy Poffin", counts, lambda o: policy.handle_main(o, [opt_play(POFFIN)], 0, 1))
run_scenario("Psychic Draw YES", counts, lambda o: policy.handle_activate(o, [opt_act(OptionType.YES, KADABRA)], 0, 1))
run_scenario("Dudunsparce ABILITY", counts, lambda o: policy.handle_activate(o, [opt_act(OptionType.ABILITY, DUDUNSPARCE)], 0, 1))
run_scenario("Dudunsparce YES", counts, lambda o: policy.handle_activate(o, [opt_act(OptionType.YES, DUDUNSPARCE)], 0, 1))

print(f"\n--- Telepathic Energy (Hard block) ---")
for dc in [40, 3, 2, 0]:
    obs.current.players[my_idx].deckCount = dc
    scores = policy.handle_attach_to(obs, [type('obj', (), {'area': AreaType.BENCH, 'index': 0})], TELEPATH_ENERGY, 0)
    print(f"Deck={dc:2} -> raw scores array: {scores}")

print(f"\n--- Enriching Energy (Hard block) ---")
for dc in [40, 5, 4, 0]:
    obs.current.players[my_idx].deckCount = dc
    scores = policy.handle_attach_to(obs, [type('obj', (), {'area': AreaType.BENCH, 'index': 0})], ENRICHING_ENERGY, 0)
    print(f"Deck={dc:2} -> raw scores array: {scores}")

