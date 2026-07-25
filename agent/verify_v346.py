import sys, os
sys.path.insert(0, os.path.dirname(__file__))

import policy as pol
from cg.api import OptionType, AreaType

class Opt:
    def __init__(self, typ, index=0, inPlayArea=AreaType.BENCH, inPlayIndex=0, area=AreaType.DECK):
        self.type = typ
        self.index = index
        self.inPlayArea = inPlayArea
        self.inPlayIndex = inPlayIndex
        self.area = area
        self.inPlayArea = inPlayArea or area

class Card:
    def __init__(self, id, hp=120, damage=0, energies=None, energyCards=None):
        self.id = id
        self.hp = hp
        self.damage = damage
        self.energies = energies or []
        self.energyCards = energyCards or []

class Player:
    def __init__(self):
        self.active = []
        self.bench = []
        self.hand = []
        self.discard = []
        self.prize = [None] * 6
        self.deckCount = 20
        self.handCount = 10
        self.asleep = self.paralyzed = self.confused = self.poisoned = self.burned = False

class State:
    def __init__(self):
        self.players = [Player(), Player()]
        self.yourIndex = 0

class Obs:
    def __init__(self, state, options, select_context=None, context_card=None):
        self.current = state
        self.options = options
        class Select:
            def __init__(self, ctx, card):
                self.context = ctx
                self.contextCard = card
        self.select = Select(select_context, context_card) if select_context else None

PASS = "\033[92m✅ PASS\033[0m"
FAIL = "\033[91m❌ FAIL\033[0m"

results = {"passed": 0, "failed": 0}

def check(name, condition, details=""):
    if condition:
        print(f"  {PASS}: {name}")
        results["passed"] += 1
    else:
        print(f"  {FAIL}: {name}  {details}")
        results["failed"] += 1

def run_attach_energy(energy_id, is_desperate, target_id=pol.SHAYMIN):
    state = State()
    my = state.players[0]
    
    target_card = Card(target_id)
    target_card.energyCards = []
    my.bench = [target_card]
    
    if is_desperate:
        my.active = [Card(pol.DUNSPARCE)] # No Alakazam line
        my.hand = []
    else:
        my.active = [Card(pol.ALAKAZAM)] # Alakazam line present -> not bricked
        my.hand = [Card(pol.HILDA)]
        
    opts = [
        Opt(OptionType.ATTACH, index=0, inPlayArea=AreaType.BENCH, inPlayIndex=0),
    ]
    
    my.hand.append(Card(energy_id))
    obs_main = Obs(state, opts)
    
    recorded_scores = []
    def fake_pick_best(scores, mn, mx, **kwargs):
        recorded_scores.extend(scores)
        return []
    
    orig_pb = pol._pick_best
    pol._pick_best = fake_pick_best
    
    def fake_get_card(obs, area, index, idx):
        if area == AreaType.HAND: return Card(energy_id)
        return target_card
        
    orig_gc = pol._get_card
    pol._get_card = fake_get_card
    
    pol.handle_main(obs_main, opts, 1, 1)
    
    score_main = recorded_scores[0] if recorded_scores else -9999.0
    recorded_scores.clear()
    
    obs_eff = Obs(state, opts, select_context=350, context_card=Card(energy_id))
    pol.handle_attach_to(obs_eff, opts, 1, 1)
    
    score_eff = recorded_scores[0] if recorded_scores else -9999.0
    
    pol._pick_best = orig_pb
    pol._get_card = orig_gc
    
    return score_main, score_eff


s_main, s_eff = run_attach_energy(pol.PSYCHIC_ENERGY, False)
check("Psychic Energy -> Shaymin = -9999 (Main)", s_main == -9999.0, f"got {s_main}")
check("Psychic Energy -> Shaymin = -9999 (Effect)", s_eff == -9999.0, f"got {s_eff}")

s_main, s_eff = run_attach_energy(pol.TELEPATH_ENERGY, False)
check("Telepathic Energy -> Shaymin = -9999 (Main)", s_main == -9999.0, f"got {s_main}")
check("Telepathic Energy -> Shaymin = -9999 (Effect)", s_eff == -9999.0, f"got {s_eff}")

s_main, s_eff = run_attach_energy(pol.ENRICHING_ENERGY, False)
check("Enriching Energy -> Shaymin (Non-Desperate) = -9999 (Main)", s_main == -9999.0, f"got {s_main}")
check("Enriching Energy -> Shaymin (Non-Desperate) = -9999 (Effect)", s_eff == -9999.0, f"got {s_eff}")

s_main, s_eff = run_attach_energy(pol.ENRICHING_ENERGY, True)
check("Enriching Energy -> Shaymin (Desperate) > 0 (Main)", s_main == 8000.0, f"got {s_main}")
check("Enriching Energy -> Shaymin (Desperate) > 0 (Effect)", s_eff == 8000.0, f"got {s_eff}")

print(f"\nResults: {results['passed']} passed, {results['failed']} failed")
if results['failed'] > 0:
    sys.exit(1)
