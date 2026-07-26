"""
v3.46c Forced-state verification:
1a. Abra switch with safe tank → 1900.0
1b. Abra switch with fighting opp → 1000.0 (Psychic resists Fighting, stay put)
1c. Abra switch with NO tank, no fighting → 1000.0 (directly tests the formerly-inverted case)
2.  handle_to_active prioritizes Dunsparce over Abra.
3a. Enriching active fallback when no Dunsparce line → 8100.0
3b. Enriching active fallback disabled when Dunsparce line present → -9999.0
4a. Shaymin fetch without bench-attacker → 8500.0
4b. Shaymin fetch with bench-attacker (Fezandipiti ex 140) → 8700.0
5a. Clefairy fetch without damage blocker revealed → 8500.0 (setup card default)
5b. Clefairy fetch with damage blocker revealed (Rabsca 74) → 8800.0
"""
import sys, os
sys.path.insert(0, os.path.abspath('.'))

from unittest.mock import patch
from cg.api import OptionType, AreaType
import policy as pol

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

# ── Mock primitives ──────────────────────────────────────────────────────────
class Opt:
    def __init__(self, type_, index=0, area=AreaType.HAND, inPlayArea=None, inPlayIndex=None):
        self.type = type_
        self.index = index
        self.area = area
        self.inPlayArea = inPlayArea or area
        self.inPlayIndex = inPlayIndex if inPlayIndex is not None else index

class Card:
    def __init__(self, id, hp=120, damage=0, energies=None, energyCards=None, pokemonType=-1):
        self.id = id
        self.hp = hp
        self.damage = damage
        self.energies = energies or []
        self.energyCards = energyCards or []
        self.pokemonType = pokemonType

class PlayerState:
    def __init__(self):
        self.active = []; self.bench = []; self.hand = []
        self.discard = []; self.prize = [1,2,3,4,5,6]; self.deckCount = 40

class State:
    def __init__(self):
        self.yourIndex = 0
        self.players = [PlayerState(), PlayerState()]

class Obs:
    def __init__(self):
        self.current = State()
        self.logs = []

# IDs (real engine values):
ABRA       = 741
DUNSPARCE  = 65
DUDUNSPARCE= 66
ALAKAZAM   = 743
SHAYMIN    = 343
CLEFAIRY   = 272
FEZANDIPITI= 140   # bench-attacker
RABSCA     = 74    # damage-blocker (Spherical Shield)

def mock_get_card(obs, area, idx, my_idx):
    st = obs.current.players[my_idx]
    if area == AreaType.ACTIVE: return st.active[idx] if idx < len(st.active) else None
    if area == AreaType.BENCH:  return st.bench[idx]  if idx < len(st.bench)  else None
    if area == AreaType.HAND:   return st.hand[idx]   if idx < len(st.hand)   else None
    if area == AreaType.DECK:   return Card(idx)
    return None

def mock_pick_best(scores, min_count, max_count, allow_empty=False):
    return scores

print("=== v3.46c Verification ===")
with patch('policy._get_card',     side_effect=mock_get_card), \
     patch('policy._pick_best',    side_effect=mock_pick_best), \
     patch('policy.evaluate_attack', return_value=500.0), \
     patch('policy.cards_needed_to_ko', return_value=999):

    # ── 1a. Abra switch — safe tank present ──────────────────────────────────
    obs = Obs()
    obs.current.players[0].active = [Card(ABRA)]
    obs.current.players[0].hand   = [Card(1)] * 5   # avoid post_disruption
    obs.current.players[0].bench  = [Card(DUNSPARCE)]
    obs.current.players[1].active = [Card(999, pokemonType=0)]  # non-fighting
    scores = pol.handle_main(obs, [Opt(OptionType.ATTACK, 0, AreaType.ACTIVE)], 1, 1)
    check("1a. Abra switch, safe tank present (1900.0)", scores[0] == 1900.0, f"Score: {scores[0]}")

    # ── 1b. Abra switch — fighting opponent ──────────────────────────────────
    obs.current.players[1].active = [Card(999, pokemonType=6)]  # fighting
    scores = pol.handle_main(obs, [Opt(OptionType.ATTACK, 0, AreaType.ACTIVE)], 1, 1)
    check("1b. Abra switch, fighting opp (1000.0)", scores[0] == 1000.0, f"Score: {scores[0]}")

    # ── 1c. Abra switch — NO tank, NO fighting (direct inversion test) ───────
    obs = Obs()
    obs.current.players[0].active = [Card(ABRA)]
    obs.current.players[0].hand   = [Card(1)] * 5
    obs.current.players[0].bench  = []              # no Dunsparce/Alakazam on bench
    obs.current.players[1].active = [Card(999, pokemonType=0)]  # non-fighting
    scores = pol.handle_main(obs, [Opt(OptionType.ATTACK, 0, AreaType.ACTIVE)], 1, 1)
    check("1c. Abra switch, no tank, no fighting (1000.0 < 1900.0)",
          scores[0] == 1000.0 and scores[0] < 1900.0, f"Score: {scores[0]}")


    # ── 1d. Abra switch — ready Alakazam present ─────────────────────────────
    obs = Obs()
    obs.current.players[0].active = [Card(ABRA)]
    obs.current.players[0].hand   = [Card(1)] * 5
    obs.current.players[0].bench  = [Card(ALAKAZAM, energies=[1])] # 1 energy = ready
    obs.current.players[1].active = [Card(999, pokemonType=0)]
    scores = pol.handle_main(obs, [Opt(OptionType.ATTACK, 0, AreaType.ACTIVE)], 1, 1)
    check("1d. Abra switch, ready Alakazam (1900.0)", scores[0] == 1900.0, f"Score: {scores[0]}")

    # ── 1e. Abra switch — unready Alakazam present ───────────────────────────
    obs.current.players[0].bench  = [Card(ALAKAZAM, energies=[])] # 0 energy = not ready
    scores = pol.handle_main(obs, [Opt(OptionType.ATTACK, 0, AreaType.ACTIVE)], 1, 1)
    check("1e. Abra switch, unready Alakazam (1000.0)", scores[0] == 1000.0, f"Score: {scores[0]}")

    # ── 2. handle_to_active: Dunsparce preferred over Abra ───────────────────
    obs = Obs()
    obs.current.players[0].bench  = [Card(ABRA), Card(DUNSPARCE)]
    obs.current.players[1].active = [Card(999, pokemonType=0)]
    opts = [Opt('dummy', 0, AreaType.BENCH), Opt('dummy', 1, AreaType.BENCH)]
    scores = pol.handle_to_active(obs, opts, 1, 1)
    check("2.  Dunsparce prioritized over Abra in handle_to_active",
          scores[1] > scores[0], f"Abra={scores[0]} Dunsparce={scores[1]}")

    # ── 3a. Enriching active fallback — no Dunsparce line ────────────────────
    obs = Obs()
    obs.current.players[0].active = [Card(ABRA)]
    obs.current.players[0].hand   = [Card(13)] * 5  # Enriching in hand
    obs.current.players[0].bench  = []
    opts = [Opt(OptionType.ATTACH, 0, AreaType.HAND, AreaType.ACTIVE, 0)]
    scores = pol.handle_main(obs, opts, 1, 1)
    check("3a. Enriching active fallback, no tank (8100.0)", scores[0] == 8100.0, f"Score: {scores[0]}")

    # ── 3b. Enriching active fallback — Dunsparce on bench (should block) ────
    obs.current.players[0].bench = [Card(DUNSPARCE)]
    scores = pol.handle_main(obs, opts, 1, 1)
    check("3b. Enriching active fallback, tank present (-9999.0)", scores[0] == -9999.0, f"Score: {scores[0]}")

    # ── 4a. Shaymin fetch — no bench attacker ────────────────────────────────
    obs = Obs()
    opts = [Opt('CHOOSE_CARDS', SHAYMIN, AreaType.DECK)]
    scores = pol.handle_to_hand(obs, opts, 1, 1)
    check("4a. Shaymin fetch, no bench attacker (8500.0)", scores[0] == 8500.0, f"Score: {scores[0]}")

    # ── 4b. Shaymin fetch — Fezandipiti ex (bench attacker) present ──────────
    obs.current.players[1].active = [Card(FEZANDIPITI)]
    scores = pol.handle_to_hand(obs, opts, 1, 1)
    check("4b. Shaymin fetch, bench attacker present (8700.0)", scores[0] == 8700.0, f"Score: {scores[0]}")

    # ── 5a. Clefairy fetch — no blocker revealed ─────────────────────────────
    obs = Obs()
    opts = [Opt('CHOOSE_CARDS', CLEFAIRY, AreaType.DECK)]
    scores = pol.handle_to_hand(obs, opts, 1, 1)
    check("5a. Clefairy fetch, no blocker (8500.0 — setup default)", scores[0] == 8500.0, f"Score: {scores[0]}")

    # ── 5b. Clefairy fetch — Rabsca (74) revealed (actual blocker target) ────
    obs.current.players[1].active = [Card(RABSCA)]   # Spherical Shield blocker
    scores = pol.handle_to_hand(obs, opts, 1, 1)
    check("5b. Clefairy fetch, Rabsca blocker (8800.0)", scores[0] == 8800.0, f"Score: {scores[0]}")

print(f"\nResults: {PASS} passed, {FAIL} failed.")
if FAIL > 0:
    sys.exit(1)
