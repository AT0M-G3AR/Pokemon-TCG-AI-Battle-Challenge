import sys, os
sys.path.insert(0, os.path.abspath('agent'))

from policy import (
    handle_main, handle_activate, handle_attach_to,
    POKE_PAD, HILDA, DAWN, POFFIN, DUDUNSPARCE, KADABRA, TELEPATH_ENERGY, ENRICHING_ENERGY
)
from cg.api import OptionType, SelectContext, AreaType

class MockCard:
    def __init__(self, cid):
        self.id = cid
        self.skills = []
        self.energies = []
        self.type = 0
    def __getitem__(self, key): # Just in case
        return getattr(self, key, 0)

class MockPlayer:
    def __init__(self, dc):
        self.deckCount = dc
        self.deck = []
        self.hand = []
        self.discard = [MockCard(1), MockCard(2)]
        self.bench = [MockCard(DUDUNSPARCE)]
        self.active = [MockCard(1)] # Active is a list in Kaggle envs!
        self.prize = []
        self.energies = []
        
class MockCurrent:
    def __init__(self, dc):
        self.yourIndex = 0
        self.players = [MockPlayer(dc), MockPlayer(dc)]
        self.rule = {}

class MockSelect:
    def __init__(self):
        self.context = SelectContext.MAIN
        self.amount = 0
        self.type = OptionType.PLAY

class MockObs:
    def __init__(self, dc):
        self.current = MockCurrent(dc)
        self.select = MockSelect()
        self.players = self.current.players 

import policy
policy._get_card = lambda obs, area, index, my_idx: MockCard(index)
policy._energy_count = lambda x: 0
policy._hp_remaining = lambda x: 60
policy._is_lethal = lambda obs, opt, card: False
policy._deck_safety_discount_orig = policy._deck_safety_discount

eval_log = []
def spy_deck_safety(deck_count, draw_amount):
    disc = policy._deck_safety_discount_orig(deck_count, draw_amount)
    eval_log.append((deck_count, draw_amount, disc))
    return disc
policy._deck_safety_discount = spy_deck_safety
policy._pick_best = lambda scores, min_c, max_c, allow_empty=False: scores

def run_scenario(name, deck_counts, fn):
    print(f"\n--- {name} ---")
    for dc in deck_counts:
        eval_log.clear()
        obs = MockObs(dc)
        try:
            scores = fn(obs)
            if eval_log:
                print(f"Deck={dc:2} -> draw={eval_log[0][1]}, penalty applied={eval_log[0][2]:8.1f}, raw scores={scores}")
            else:
                print(f"Deck={dc:2} -> (No safety evaluation), raw scores={scores}")
        except Exception as e:
            print(f"Deck={dc:2} -> Error: {e}")
            import traceback
            traceback.print_exc()

counts = [40, 5, 4, 3, 2, 1, 0]

opt_play = lambda cid: type('obj', (), {'type': OptionType.PLAY, 'area': AreaType.HAND, 'index': cid, 'target': KADABRA})
opt_act = lambda t, cid: type('obj', (), {'type': t, 'area': AreaType.BENCH, 'index': cid, 'target': KADABRA})

run_scenario("Poké Pad", counts, lambda o: handle_main(o, [opt_play(POKE_PAD)], 0, 1))
run_scenario("Hilda", counts, lambda o: handle_main(o, [opt_play(HILDA)], 0, 1))
run_scenario("Dawn", counts, lambda o: handle_main(o, [opt_play(DAWN)], 0, 1))
run_scenario("Buddy-Buddy Poffin", counts, lambda o: handle_main(o, [opt_play(POFFIN)], 0, 1))
run_scenario("Psychic Draw YES", counts, lambda o: handle_activate(o, [opt_act(OptionType.YES, KADABRA)], 0, 1))
run_scenario("Dudunsparce ABILITY", counts, lambda o: handle_activate(o, [opt_act(OptionType.ABILITY, DUDUNSPARCE)], 0, 1))
run_scenario("Dudunsparce YES", counts, lambda o: handle_activate(o, [opt_act(OptionType.YES, DUDUNSPARCE)], 0, 1))

print(f"\n--- Telepathic Energy (Hard block) ---")
for dc in [40, 3, 2, 0]:
    o = MockObs(dc)
    scores = handle_attach_to(o, [type('obj', (), {'area': AreaType.BENCH, 'index': 0, 'type': 0, 'target': KADABRA})], TELEPATH_ENERGY, 0)
    print(f"Deck={dc:2} -> raw scores array: {scores}")

print(f"\n--- Enriching Energy (Hard block) ---")
for dc in [40, 5, 4, 0]:
    o = MockObs(dc)
    scores = handle_attach_to(o, [type('obj', (), {'area': AreaType.BENCH, 'index': 0, 'type': 0, 'target': KADABRA})], ENRICHING_ENERGY, 0)
    print(f"Deck={dc:2} -> raw scores array: {scores}")
