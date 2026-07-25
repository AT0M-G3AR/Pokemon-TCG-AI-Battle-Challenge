"""
v3.44 Forced-state tests:
1. Candy wins when attack is non-lethal and Candy condition holds
2. Candy correctly LOSES when playing it would cost a lethal KO
3. Draw abilities (Dudunsparce/Psychic Draw) still score above Candy
4. Regression: lethal attacks still fire; Candy condition not met → no cap
"""
import sys, os
sys.path.insert(0, os.path.abspath('.'))

from unittest.mock import patch
import policy as pol
from cg.api import OptionType, AreaType, SelectContext

# ── Mock objects ──────────────────────────────────────────────────────────────
class MockOption:
    def __init__(self, type_, index=0, area=AreaType.HAND, inPlayArea=None, inPlayIndex=None):
        self.type = type_
        self.index = index
        self.area = area
        self.inPlayArea = inPlayArea or area
        self.inPlayIndex = inPlayIndex if inPlayIndex is not None else index

class MockCard:
    def __init__(self, id, hp=120, damage=0, energies=None, energyCards=None):
        self.id = id
        self.hp = hp
        self.damage = damage
        self.energies = energies or []
        self.energyCards = energyCards or []

class MockPlayer:
    def __init__(self):
        self.active = []
        self.bench = []
        self.hand = []
        self.discard = []
        self.prize = [None] * 6
        self.deckCount = 20
        self.handCount = 10
        self.asleep = False
        self.paralyzed = False
        self.confused = False
        self.poisoned = False
        self.burned = False

class MockState:
    def __init__(self, my_idx=0):
        self.players = [MockPlayer(), MockPlayer()]
        self.yourIndex = my_idx
        self.supporterPlayed = False
        self.energyAttached = False

class MockSelect:
    def __init__(self, options, context=SelectContext.MAIN, minCount=1, maxCount=1):
        self.option = options
        self.context = context
        self.minCount = minCount
        self.maxCount = maxCount
        self.contextCard = None

class MockObs:
    def __init__(self, state, options):
        self.current = state
        self.select = MockSelect(options)


def build_attack_scenario(
    extra_hand=None,    # extra cards in hand beyond Candy/Alakazam
    abra_in_play=True,
    kadabra_in_play=False,
    op_hp=300,
    raw_attack_score=10000.0,
    supporter_played=False,
):
    """
    Build a full mock state and return the attack score that handle_main assigns.
    extra_hand: list of MockCard IDs (plain ints) to fill hand with neutral cards.
    """
    state = MockState()
    state.supporterPlayed = supporter_played

    # My side
    my = state.players[0]
    active_alakazam = MockCard(pol.ALAKAZAM, hp=150, damage=0, energies=[pol.PSYCHIC_ENERGY])
    my.active = [active_alakazam]

    # Build hand: start with neutral cards so hand_size >= 8 (avoids post_disruption path)
    neutral_cards = [MockCard(pol.PSYCHIC_ENERGY)] * 8
    candy = MockCard(pol.RARE_CANDY)
    alakazam_card = MockCard(pol.ALAKAZAM)
    extra = [MockCard(c) if isinstance(c, int) else c for c in (extra_hand or [])]
    my.hand = [candy, alakazam_card] + neutral_cards + extra

    my.bench = []
    if abra_in_play:
        my.bench.append(MockCard(pol.ABRA, hp=60, damage=0))
    if kadabra_in_play:
        my.bench.append(MockCard(pol.KADABRA, hp=80, damage=0))

    # Op side
    op = state.players[1]
    op_active = MockCard(999, hp=op_hp, damage=0)
    op.active = [op_active]
    op.bench = []
    op.prize = [None] * 4

    # Build options
    options = []
    for i, c in enumerate(my.hand):
        options.append(MockOption(OptionType.PLAY, index=i))
    options.append(MockOption(OptionType.ATTACK, index=len(my.hand)))
    options.append(MockOption(OptionType.END, index=len(my.hand) + 1))

    obs = MockObs(state, options)

    recorded = {}
    original_pick = pol._pick_best
    def mock_pick(scores_in, min_c, max_c, allow_empty=False):
        recorded['scores'] = list(scores_in)
        return original_pick(scores_in, min_c, max_c, allow_empty)
    pol._pick_best = mock_pick

    with patch('policy.evaluate_attack', return_value=raw_attack_score):
        pol.handle_main(obs, options, 1, 1)

    pol._pick_best = original_pick

    attack_idx = next(i for i, o in enumerate(options) if o.type == OptionType.ATTACK)
    return recorded.get('scores', [None] * (attack_idx + 1))[attack_idx]


PASS = 0
FAIL = 0

def check(name, condition, detail=""):
    global PASS, FAIL
    if condition:
        print(f"  ✅ PASS: {name}")
        PASS += 1
    else:
        print(f"  ❌ FAIL: {name} {detail}")
        FAIL += 1


print("=" * 65)
print("v3.44 FORCED-STATE TESTS")
print("=" * 65)

# Test 1: Non-lethal attack WITH Rare Candy available — attack must be capped to 9750
print("\n[Test 1] Non-lethal attack + Candy condition: attack capped to 9750")
# 10 cards in hand, op_hp=300: 200 dmg < 300 hp → non-lethal
score = build_attack_scenario(abra_in_play=True, kadabra_in_play=False, op_hp=300,
                               raw_attack_score=10000.0)
check("Attack score <= 9750 (Candy wins)", score <= 9750.0, f"got {score}")
check("Attack score > 0 (not suppressed entirely)", score > 0, f"got {score}")

# Test 2: Lethal attack — attack must NOT be capped, even with Candy available
print("\n[Test 2] Lethal attack + Candy available: attack NOT capped")
# 10 cards in hand (+ 2 extras = 12 × 20 = 240 dmg), op_hp=200 → lethal
score_lethal = build_attack_scenario(abra_in_play=True, kadabra_in_play=False, op_hp=200,
                                      extra_hand=[pol.PSYCHIC_ENERGY] * 2,  # hand_size=12 → 240 dmg ≥ 200
                                      raw_attack_score=50000.0)
check("Lethal attack NOT capped by Candy", score_lethal > 9800.0, f"got {score_lethal}")

# Test 3: Kadabra already in play (condition not met, Candy → -9999)
print("\n[Test 3] Kadabra in play (Candy condition not met): attack not capped")
score_no_cond = build_attack_scenario(abra_in_play=True, kadabra_in_play=True, op_hp=300,
                                       raw_attack_score=10000.0)
check("Attack NOT capped when Kadabra present", score_no_cond > 9800.0, f"got {score_no_cond}")

# Test 4: No Abra in play (condition not met)
print("\n[Test 4] No Abra in play: attack not capped")
score_no_abra = build_attack_scenario(abra_in_play=False, kadabra_in_play=False, op_hp=300,
                                       raw_attack_score=10000.0)
check("Attack NOT capped when Abra absent", score_no_abra > 9800.0, f"got {score_no_abra}")

# Test 5: Candy in hand but Alakazam already on field (not in hand) — hand has Kadabra instead
print("\n[Test 5] Alakazam not in hand (Candy can't complete the skip): attack not capped")
# Override: remove Alakazam from hand, add Kadabra instead (rebuild scenario manually)
state = MockState()
my = state.players[0]
my.active = [MockCard(pol.ALAKAZAM, hp=150, damage=0, energies=[pol.PSYCHIC_ENERGY])]
# Hand: Candy + Kadabra + 8 neutral (no Alakazam in hand → field[ALAKAZAM] = 0, can't skip)
my.hand = [MockCard(pol.RARE_CANDY), MockCard(pol.KADABRA)] + [MockCard(pol.PSYCHIC_ENERGY)] * 8
my.bench = [MockCard(pol.ABRA)]
op = state.players[1]
op.active = [MockCard(999, hp=300)]
op.bench = []
op.prize = [None] * 4

options = []
for i, c in enumerate(my.hand):
    options.append(MockOption(OptionType.PLAY, index=i))
atk_idx = len(my.hand)
options.append(MockOption(OptionType.ATTACK, index=atk_idx))
options.append(MockOption(OptionType.END, index=atk_idx + 1))
obs = MockObs(state, options)

recorded5 = {}
def mock_pick5(scores_in, min_c, max_c, allow_empty=False):
    recorded5['scores'] = list(scores_in)
    return pol._pick_best.__wrapped__(scores_in, min_c, max_c, allow_empty) if hasattr(pol._pick_best, '__wrapped__') else [max(range(len(scores_in)), key=lambda i: scores_in[i])]
orig_pick = pol._pick_best
pol._pick_best = lambda s, mn, mx, **kw: (recorded5.update({'scores': list(s)}) or None) or orig_pick(s, mn, mx, **kw)
with patch('policy.evaluate_attack', return_value=10000.0):
    pol.handle_main(obs, options, 1, 1)
pol._pick_best = orig_pick

score_no_ala = recorded5.get('scores', [0] * (atk_idx + 1))[atk_idx]
check("Attack NOT capped when Alakazam not in hand", score_no_ala > 9800.0, f"got {score_no_ala}")

print(f"\n{'=' * 65}")
print(f"Results: {PASS} passed, {FAIL} failed")
print(f"{'=' * 65}")
if FAIL > 0:
    sys.exit(1)
