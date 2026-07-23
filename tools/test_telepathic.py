import sys, os
sys.path.insert(0, os.path.abspath('agent'))
from policy import handle_attach_to, TELEPATH_ENERGY, KADABRA
from cg.api import OptionType, SelectContext, AreaType

class MockCard:
    def __init__(self, cid):
        self.id = cid
        self.skills = []
        self.energies = []
        self.type = 0

class MockPlayer:
    def __init__(self, dc):
        self.deckCount = dc
        self.deck = []
        self.hand = []
        self.discard = [MockCard(1), MockCard(2)]
        self.bench = [MockCard(KADABRA)]
        self.active = [MockCard(1)]
        self.prize = []
        self.energies = []
        
class MockCurrent:
    def __init__(self, dc):
        self.yourIndex = 0
        self.players = [MockPlayer(dc), MockPlayer(dc)]
        self.rule = {}

class MockSelect:
    def __init__(self, energy_id):
        self.context = SelectContext.MAIN
        self.amount = 0
        self.type = OptionType.PLAY
        self.contextCard = MockCard(energy_id)

class MockObs:
    def __init__(self, dc, energy_id):
        self.current = MockCurrent(dc)
        self.select = MockSelect(energy_id)
        self.players = self.current.players 

import policy
policy._get_card = lambda obs, area, index, my_idx: MockCard(index) # index is KADABRA here
policy._energy_count = lambda x: 0
policy._hp_remaining = lambda x: 60
policy._is_lethal = lambda obs, opt, card: False
policy._pick_best = lambda scores, min_c, max_c, allow_empty=False: scores

print(f"\n--- Telepathic Energy (Hard block) ---")
for dc in [40, 3, 2, 0]:
    o = MockObs(dc, TELEPATH_ENERGY)
    # The option index must be KADABRA for _get_card to return a card with id KADABRA
    scores = handle_attach_to(o, [type('obj', (), {'inPlayArea': AreaType.BENCH, 'inPlayIndex': KADABRA})], 0, 1)
    print(f"Deck={dc:2} -> raw scores array: {scores}")
