"""
v3.45 Forced-state verification:
1. Battle Cage: high priority (8500 baseline, 10500 in Dragapult matchup / opp stadium)
2. Rule A: non-lethal attack into Dragapult ex is capped ≤1800; lethal NOT capped
3. Rule B: Munkidori live + high-HP target → attack capped ≤1800; small KO-able target NOT capped
4. Rule C: Drakloak KO-able → +3000 bonus in _target_score; ordering vs blocker bonus (+5000)
5. Nighttime Mine dead-code: NIGHTTIME_MINE is no longer scored when in our hand
6. Count-sensitive thresholds: dunsparce_field < 3 still reachable with 3-copy deck
"""
import sys, os
sys.path.insert(0, os.path.abspath('.'))

from unittest.mock import patch, MagicMock
import policy as pol
from cg.api import OptionType, AreaType, SelectContext

PASS = 0
FAIL = 0

def check(name, condition, detail=""):
    global PASS, FAIL
    if condition:
        print(f"  ✅ PASS: {name}")
        PASS += 1
    else:
        print(f"  ❌ FAIL: {name}  {detail}")
        FAIL += 1


# ── Mock helpers ──────────────────────────────────────────────────────────────
class Opt:
    def __init__(self, type_, index=0, area=AreaType.HAND, inPlayArea=None, inPlayIndex=None):
        self.type = type_
        self.index = index
        self.area = area
        self.inPlayArea = inPlayArea or area
        self.inPlayIndex = inPlayIndex if inPlayIndex is not None else index

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
        self.supporterPlayed = False
        self.energyAttached = False
        self.stadium = None  # no stadium by default

class Sel:
    def __init__(self, options):
        self.option = options
        self.context = SelectContext.MAIN
        self.minCount = 1
        self.maxCount = 1
        self.contextCard = None

class Obs:
    def __init__(self, state, options):
        self.current = state
        self.select = Sel(options)

def get_scores(state, options, raw_attack_score=10000.0):
    """Run handle_main and return the scores list."""
    obs = Obs(state, options)
    recorded = {}
    orig = pol._pick_best
    pol._pick_best = lambda s, mn, mx, **kw: recorded.update({'scores': list(s)}) or orig(s, mn, mx, **kw)
    with patch('policy.evaluate_attack', return_value=raw_attack_score):
        pol.handle_main(obs, options, 1, 1)
    pol._pick_best = orig
    return recorded.get('scores', [])


# ── Section 1: Battle Cage scoring ────────────────────────────────────────────
print("=" * 62)
print("[1] Battle Cage play priority")
print("=" * 62)

def cage_score(in_dragapult=False, opp_has_stadium=False, our_cage_in_play=False):
    state = State()
    my = state.players[0]
    my.active = [Card(pol.KADABRA, energies=[pol.PSYCHIC_ENERGY])]
    my.hand = [Card(pol.BATTLE_CAGE)] + [Card(pol.PSYCHIC_ENERGY)] * 9

    op = state.players[1]
    op.active = [Card(pol.DREEPY if in_dragapult else 999, hp=70)]
    op.bench = []
    op.prize = [None] * 4

    if opp_has_stadium:
        # API: stadium is list[Card]; opponent's non-Cage stadium (e.g. Jamming Tower = some other ID)
        state.stadium = [Card(9999)]  # non-BATTLE_CAGE ID → op_has_stadium = True
    elif our_cage_in_play:
        state.stadium = [Card(pol.BATTLE_CAGE)]

    options = [Opt(OptionType.PLAY, index=0)]  # Battle Cage in hand[0]
    for i in range(1, len(my.hand)):
        options.append(Opt(OptionType.PLAY, index=i))
    options.append(Opt(OptionType.ATTACK, index=len(my.hand)))
    options.append(Opt(OptionType.END, index=len(my.hand)+1))

    scores = get_scores(state, options)
    return scores[0]  # Battle Cage is option 0

sc_base     = cage_score(in_dragapult=False, opp_has_stadium=False)
sc_dragapult= cage_score(in_dragapult=True,  opp_has_stadium=False)
sc_stadium  = cage_score(in_dragapult=False, opp_has_stadium=True)
sc_our_cage = cage_score(our_cage_in_play=True)

check("Battle Cage baseline score ≥ 8500",   sc_base >= 8500.0,    f"got {sc_base}")
check("Battle Cage in Dragapult = 10500",     sc_dragapult == 10500.0, f"got {sc_dragapult}")
check("Battle Cage opp stadium = 10500",      sc_stadium == 10500.0,   f"got {sc_stadium}")
check("Battle Cage our Cage in play = -9999", sc_our_cage == -9999.0,  f"got {sc_our_cage}")
check("Dragapult/stadium > baseline",         sc_dragapult > sc_base,  f"{sc_dragapult} vs {sc_base}")


# ── Section 2: Rule A — Don't chip Dragapult ex ───────────────────────────────
print("\n" + "=" * 62)
print("[2] Rule A: Non-lethal attack into Dragapult ex is capped ≤1800")
print("=" * 62)

def dragapult_attack_score(op_hp, raw_score=10000.0):
    state = State()
    my = state.players[0]
    my.active = [Card(pol.ALAKAZAM, energies=[pol.PSYCHIC_ENERGY])]
    my.hand = [Card(pol.PSYCHIC_ENERGY)] * 10  # 10 cards → 200 dmg

    op = state.players[1]
    op.active = [Card(pol.DRAGAPULT_EX, hp=op_hp, damage=0)]
    op.bench = []
    op.prize = [None] * 4

    options = [Opt(OptionType.ATTACK, index=0), Opt(OptionType.END, index=1)]
    scores = get_scores(state, options, raw_attack_score=raw_score)
    return scores[0]

# Non-lethal into 320 HP Dragapult (200 dmg < 320 hp)
sc_chip_dragapult = dragapult_attack_score(op_hp=320)
check("Non-lethal chip into Dragapult ex ≤ 1800", sc_chip_dragapult <= 1800.0, f"got {sc_chip_dragapult}")

# Lethal into Dragapult ex (200 dmg = 200 hp — if Dragapult somehow has 200 HP left)
sc_lethal_dragapult = dragapult_attack_score(op_hp=200)
check("Lethal attack into Dragapult ex NOT capped", sc_lethal_dragapult > 9800.0, f"got {sc_lethal_dragapult}")

# Non-lethal into a small generic (Drakloak 90 HP) — Rule A should NOT apply
def small_target_attack_score(op_id, op_hp, raw_score=10000.0):
    state = State()
    my = state.players[0]
    my.active = [Card(pol.ALAKAZAM, energies=[pol.PSYCHIC_ENERGY])]
    my.hand = [Card(pol.PSYCHIC_ENERGY)] * 10

    op = state.players[1]
    op.active = [Card(op_id, hp=op_hp)]
    op.bench = []
    op.prize = [None] * 4

    options = [Opt(OptionType.ATTACK, index=0), Opt(OptionType.END, index=1)]
    scores = get_scores(state, options, raw_attack_score=raw_score)
    return scores[0]

sc_generic_small = small_target_attack_score(999, op_hp=90)
check("Non-lethal into small generic (90 HP) NOT capped by Rule A",
      sc_generic_small > 1800.0, f"got {sc_generic_small}")


# ── Section 3: Rule B — Munkidori counter-theft discount ──────────────────────
print("\n" + "=" * 62)
print("[3] Rule B: Munkidori live + high-HP target → attack capped")
print("=" * 62)

def munkidori_attack_score(op_active_hp, munkidori_in_bench=True, raw_score=10000.0):
    state = State()
    my = state.players[0]
    my.active = [Card(pol.ALAKAZAM, energies=[pol.PSYCHIC_ENERGY])]
    my.hand = [Card(pol.PSYCHIC_ENERGY)] * 10  # 200 dmg

    op = state.players[1]
    op.active = [Card(999, hp=op_active_hp)]  # generic high-HP non-Dragapult target
    op.bench = [Card(pol.MUNKIDORI, hp=110)] if munkidori_in_bench else []
    op.prize = [None] * 4

    options = [Opt(OptionType.ATTACK, index=0), Opt(OptionType.END, index=1)]
    scores = get_scores(state, options, raw_attack_score=raw_score)
    return scores[0]

# Munkidori live + high-HP target (210 HP) — non-lethal (200 < 210)
sc_munkidori_high = munkidori_attack_score(op_active_hp=210, munkidori_in_bench=True)
check("Munkidori live + 210 HP target → capped ≤ 1800", sc_munkidori_high <= 1800.0, f"got {sc_munkidori_high}")

# Munkidori live + small target (90 HP) — lethal at 200 dmg, so NOT capped by Rule B
sc_munkidori_small = munkidori_attack_score(op_active_hp=90, munkidori_in_bench=True)
check("Munkidori live + 90 HP target (lethal) → NOT capped", sc_munkidori_small > 1800.0, f"got {sc_munkidori_small}")

# No Munkidori in play + high-HP target — Rule B should NOT apply
sc_no_munkidori_high = munkidori_attack_score(op_active_hp=210, munkidori_in_bench=False)
check("No Munkidori + 210 HP target → NOT capped by Rule B", sc_no_munkidori_high > 1800.0, f"got {sc_no_munkidori_high}")


# ── Section 4: Rule C — Drakloak snipe bonus in _target_score ─────────────────
print("\n" + "=" * 62)
print("[4] Rule C: Drakloak snipe bonus; ordering vs blocker bonus")
print("=" * 62)

hand_size = 10
current_dmg = hand_size * 20  # 200 dmg

# Drakloak at 90 HP — lethal at 200 dmg
drakloak = Card(pol.DRAKLOAK, hp=90, damage=0)
sc_drakloak = pol._target_score(drakloak, my_prizes_left=4, current_damage=current_dmg)

# Blocker at 90 HP — lethal at 200 dmg
blocker = Card(pol.TEAM_ROCKETS_ARTICUNO, hp=90, damage=0)
sc_blocker = pol._target_score(blocker, my_prizes_left=4, current_damage=current_dmg)

# Generic at 90 HP — lethal at 200 dmg
generic = Card(999, hp=90, damage=0)
sc_generic = pol._target_score(generic, my_prizes_left=4, current_damage=current_dmg)

# Drakloak at 300 HP — non-lethal (no lethal bonus should fire)
drakloak_hp300 = Card(pol.DRAKLOAK, hp=300, damage=0)
sc_drakloak_nonlethal = pol._target_score(drakloak_hp300, my_prizes_left=4, current_damage=current_dmg)

check(f"Drakloak (KO-able) > generic (KO-able)",
      sc_drakloak > sc_generic, f"Drakloak={sc_drakloak:.1f}, generic={sc_generic:.1f}")
check(f"Blocker (KO-able) > Drakloak (KO-able) — ordering preserved",
      sc_blocker > sc_drakloak, f"Blocker={sc_blocker:.1f}, Drakloak={sc_drakloak:.1f}")
check("Drakloak NOT KO-able → no Rule C bonus",
      sc_drakloak_nonlethal < sc_drakloak, f"non-lethal={sc_drakloak_nonlethal:.1f} vs KO={sc_drakloak:.1f}")
print(f"\n  Scores: blocker={sc_blocker:.1f}, Drakloak={sc_drakloak:.1f}, generic={sc_generic:.1f}")
print(f"  Drakloak bonus delta: +{sc_drakloak - sc_generic:.1f} (expected +3000)")
check("Drakloak Rule C bonus = exactly +3000", abs((sc_drakloak - sc_generic) - 3000.0) < 0.1,
      f"delta={sc_drakloak - sc_generic:.1f}")


# ── Section 5: Nighttime Mine — no longer scored from hand ────────────────────
print("\n" + "=" * 62)
print("[5] Nighttime Mine dead-code confirmation")
print("=" * 62)

state = State()
my = state.players[0]
my.active = [Card(pol.ALAKAZAM, energies=[pol.PSYCHIC_ENERGY])]
my.hand = [Card(pol.NIGHTTIME_MINE)] + [Card(pol.PSYCHIC_ENERGY)] * 9
op = state.players[1]
op.active = [Card(999, hp=200)]
op.bench = []
op.prize = [None] * 4

nm_options = [Opt(OptionType.PLAY, index=0)]
for i in range(1, len(my.hand)):
    nm_options.append(Opt(OptionType.PLAY, index=i))
nm_options.append(Opt(OptionType.END, index=len(my.hand)))
nm_scores = get_scores(state, nm_options)
nm_score = nm_scores[0] if nm_scores else 0

# With dead code, Nighttime Mine falls through to the generic `else: score = 1000.0` branch
check("Nighttime Mine falls through to generic scorer (≤ 1000, not 2500/8000)",
      nm_score <= 1000.0, f"got {nm_score}")

# ── Section 6: Count-threshold check ──────────────────────────────────────────
print("\n" + "=" * 62)
print("[6] Count-sensitive threshold: dunsparce_field < 3 still reachable")
print("=" * 62)
# With 3x Dunsparce in deck, max field copies is 3 (all 3 benched).
# Check that placing 2 Dunsparce on bench (dunsparce_field=2) still allows a 3rd.
state2 = State()
my2 = state2.players[0]
my2.active = [Card(pol.ALAKAZAM, energies=[pol.PSYCHIC_ENERGY])]
my2.hand = [Card(pol.DUNSPARCE)] + [Card(pol.PSYCHIC_ENERGY)] * 9  # Dunsparce in hand
my2.bench = [Card(pol.DUNSPARCE), Card(pol.DUNSPARCE)]  # 2 already on bench
op2 = state2.players[1]
op2.active = [Card(999, hp=200)]
op2.bench = []
op2.prize = [None] * 4

ds_options = [Opt(OptionType.PLAY, index=0)]  # Dunsparce in hand[0]
for i in range(1, len(my2.hand)):
    ds_options.append(Opt(OptionType.PLAY, index=i))
ds_options.append(Opt(OptionType.END, index=len(my2.hand)))
ds_scores = get_scores(state2, ds_options)
ds_score = ds_scores[0]

# dunsparce_field = 2 (< 3) → should score 5500.0
check("Dunsparce playable when 2 already on bench (dunsparce_field=2 < 3)",
      ds_score > 0, f"got {ds_score}")
print(f"  Dunsparce score with 2 on bench: {ds_score} (expected 5500 or similar)")

# With all 3 on bench, should be suppressed
my2.bench = [Card(pol.DUNSPARCE), Card(pol.DUNSPARCE), Card(pol.DUNSPARCE)]
ds_scores2 = get_scores(state2, ds_options)
ds_score2 = ds_scores2[0]
check("Dunsparce suppressed when 3 already on bench (dunsparce_field=3, not < 3)",
      ds_score2 <= 0, f"got {ds_score2}")


# ── Section 7: Battle Cage sequencing (v3.45b Flag 1 boost design) ────────────
print("\n" + "=" * 62)
print("[7] Battle Cage sequencing: Cage PLAY score boosted to beat everything")
print("=" * 62)

def cage_seq_play_score(hand_size, op_hp, include_cage=True):
    """Play score of Battle Cage given the attack situation."""
    state = State()
    my = state.players[0]
    my.active = [Card(pol.ALAKAZAM, hp=150, energies=[pol.PSYCHIC_ENERGY])]
    my.hand = [Card(pol.PSYCHIC_ENERGY)] * hand_size
    if include_cage:
        my.hand = [Card(pol.BATTLE_CAGE)] + my.hand

    op = state.players[1]
    op.active = [Card(999, hp=op_hp, damage=0)]
    op.bench = []
    op.prize = [None] * 4

    options = []
    if include_cage:
        options.append(Opt(OptionType.PLAY, index=0))  # Cage at index 0
    for i in range(len(my.hand) - (1 if include_cage else 0)):
        options.append(Opt(OptionType.PLAY, index=i + (1 if include_cage else 0)))
    atk_idx = len(options)
    options.append(Opt(OptionType.ATTACK, index=atk_idx))
    options.append(Opt(OptionType.END, index=atk_idx + 1))

    scores = get_scores(state, options, raw_attack_score=10000.0)
    
    if include_cage:
        return scores[0]  # Cage PLAY score
    return scores[atk_idx] # fallback to return attack score if no cage

# Case C: Non-lethal attack with Cage in hand → Cage boosted
sc_nonlethal_cage = cage_seq_play_score(hand_size=10, op_hp=300, include_cage=True)
check("Case C: non-lethal attack → Cage PLAY score boosted to 55000",
      sc_nonlethal_cage == 55000.0, f"got {sc_nonlethal_cage}")

# Case A: Lethal-with-margin — safe to play Cage first
sc_lethal_margin_cage = cage_seq_play_score(hand_size=15, op_hp=250, include_cage=True)
check("Case A: lethal-with-margin → Cage PLAY score boosted to 55000",
      sc_lethal_margin_cage == 55000.0, f"got {sc_lethal_margin_cage}")

# Case B: Lethal-would-break — Cage would break KO
sc_lethal_tight_cage = cage_seq_play_score(hand_size=10, op_hp=210, include_cage=True)
check("Case B: lethal-would-break → Cage PLAY score heavily discounted (-9999)",
      sc_lethal_tight_cage == -9999.0, f"got {sc_lethal_tight_cage}")

print(f"\n{'=' * 62}")
print(f"Results: {PASS} passed, {FAIL} failed")
print(f"{'=' * 62}")
if FAIL > 0:
    sys.exit(1)
