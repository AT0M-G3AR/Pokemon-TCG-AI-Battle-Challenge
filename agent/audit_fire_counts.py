"""
Phase 2 fire-count audit — v2. Addresses review corrections:
1. Mist rows → N/A (opponent has none in self-play)
2. Real counts for deck-safety, lethal-guard, poke-pad, lethal_now
3. Per-TURN Rare Candy conversion (not per-evaluation)
"""
import sys, os, time
from collections import defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'agent'))

import policy as _pol

_counters = defaultdict(int)

# Per-turn Rare Candy tracking:
# key = (game_id, turn_id), value = {'condition_met': bool, 'played': bool}
_candy_turns = {}
_current_game = [0]
_current_turn = [0]
_turn_candy_condition = [False]
_turn_candy_played = [False]

def _flush_turn():
    """Record turn data and reset per-turn trackers."""
    k = (_current_game[0], _current_turn[0])
    if _turn_candy_condition[0]:
        _candy_turns[k] = _turn_candy_played[0]
    _turn_candy_condition[0] = False
    _turn_candy_played[0] = False

_orig_handle_main      = _pol.handle_main
_orig_handle_to_hand   = _pol.handle_to_hand
_orig_handle_attach_to = _pol.handle_attach_to

def _patched_handle_main(obs, options, min_count, max_count):
    from cg.api import OptionType, AreaType

    state    = obs.current
    my_idx   = state.yourIndex
    my_state = state.players[my_idx]
    op_state = state.players[1 - my_idx]
    field    = _pol._field_counts(state, my_idx)
    hand     = _pol._hand_counts(state, my_idx)
    active   = my_state.active[0] if my_state.active else None
    op_active= op_state.active[0] if op_state.active else None
    op_bench = [p for p in op_state.bench if p is not None]
    supporter_played = getattr(state, 'supporterPlayed', False)

    # Turn signal: new handle_main call with END in options = new turn beginning
    has_end = any(o.type == OptionType.END for o in options)
    if has_end:
        _flush_turn()
        _current_turn[0] += 1

    # ── v3.42 Fix 1: Wasteful retreat guard ───────────────────────────────
    if active and active.id not in (_pol.ALAKAZAM, _pol.ALAKAZAM_TWM,
                                     _pol.DUNSPARCE, _pol.DUDUNSPARCE):
        alakazam_ready = any(
            p and p.id == _pol.ALAKAZAM and _pol._energy_count(p) >= 1
            for p in my_state.bench if p)
        my_status_curable = (getattr(my_state, 'confused', False) or
                             getattr(my_state, 'poisoned', False) or
                             getattr(my_state, 'burned', False))
        if _pol._energy_count(active) >= 1 and not my_status_curable and not alakazam_ready:
            card_data = _pol.CARD_DB.get(active.id)
            max_hp = getattr(card_data, 'hp', 999) if card_data else 999
            if _pol._hp_remaining(active) >= max_hp:
                _counters['FIRED_v342_retreat_guard'] += 1

    # ── v3.39: Lethal-first card play guard ───────────────────────────────
    is_lethal = _pol._lethal_now(state, my_idx, 1 - my_idx)
    if is_lethal:
        _counters['FIRED_v341_lethal_now_true'] += 1

    op_hp = _pol._hp_remaining(op_active) if op_active else 999
    for o in options:
        if o.type == OptionType.PLAY and is_lethal:
            card = _pol._get_card(obs, AreaType.HAND, o.index, my_idx)
            if card and card.id not in (_pol.ENH_HAMMER, _pol.BOSS_ORDERS):
                my_active_obj = next((p for p in my_state.active if p), None)
                if my_active_obj and my_active_obj.id == _pol.ALAKAZAM:
                    current_hand = len(my_state.hand)
                    # -1 is conservative net_change for most trainer cards
                    if (current_hand - 1) * 20 < op_hp:
                        _counters['FIRED_v339_lethal_guard_blocked'] += 1
                        break  # count per evaluation not per card

    # ── v3.42 Fix 3: Rare Candy — per-EVALUATION and per-TURN ────────────
    for o in options:
        if o.type == OptionType.PLAY:
            card = _pol._get_card(obs, AreaType.HAND, o.index, my_idx)
            if card and card.id == _pol.RARE_CANDY:
                _counters['EVALUATED_v342_rare_candy'] += 1
                if (field[_pol.ABRA] > 0 and hand[_pol.ALAKAZAM] > 0
                        and field[_pol.KADABRA] == 0):
                    _counters['FIRED_v342_rare_candy_eval'] += 1
                    _turn_candy_condition[0] = True  # condition met this turn

    # ── Deck safety: count non-zero penalty applications ─────────────────
    deck = my_state.deckCount
    for draw_amount in [1, 2, 3]:
        disc = _pol._deck_safety_discount(deck, draw_amount)
        if disc < 0:
            _counters[f'FIRED_deck_safety_draw{draw_amount}'] += 1

    # ── Poke Pad context-aware: which branch fires ─────────────────────
    for o in options:
        if o.type == OptionType.PLAY:
            card = _pol._get_card(obs, AreaType.HAND, o.index, my_idx)
            if card and card.id == _pol.POKE_PAD:
                _counters['EVALUATED_poke_pad'] += 1
                alakazam_line_field = (field[_pol.ABRA] + field[_pol.KADABRA] +
                                       field[_pol.ALAKAZAM] + field[_pol.ALAKAZAM_TWM])
                dunsparce_field = field[_pol.DUNSPARCE] + field[_pol.DUDUNSPARCE]
                if alakazam_line_field < 2 or dunsparce_field < 1:
                    _counters['FIRED_poke_pad_priority_branch'] += 1  # score=6000
                else:
                    _counters['FIRED_poke_pad_fallback_branch'] += 1  # score=5000

    # ── v3.43: Boss's Orders blocker snipe ────────────────────────────────
    for o in options:
        if o.type == OptionType.PLAY:
            card = _pol._get_card(obs, AreaType.HAND, o.index, my_idx)
            if card and card.id == _pol.BOSS_ORDERS:
                if not supporter_played and op_bench:
                    _counters['EVALUATED_v343_boss_orders'] += 1
                    if any(p.id in _pol.DAMAGE_BLOCKING_ABILITY_IDS for p in op_bench):
                        _counters['FIRED_v343_boss_blocker_snipe'] += 1

    result = _orig_handle_main(obs, options, min_count, max_count)

    # What was selected?
    chosen = set(result)
    for i, o in enumerate(options):
        if i in chosen:
            if o.type == OptionType.PLAY:
                card = _pol._get_card(obs, AreaType.HAND, o.index, my_idx)
                if card:
                    if card.id == _pol.RARE_CANDY:
                        _counters['SELECTED_v342_rare_candy_eval'] += 1
                        _turn_candy_played[0] = True
                    elif card.id == _pol.BOSS_ORDERS:
                        _counters['SELECTED_boss_orders_any'] += 1
                    elif card.id == _pol.DAWN:
                        _counters['SELECTED_dawn'] += 1
                    elif card.id == _pol.HILDA:
                        _counters['SELECTED_hilda'] += 1
                    elif card.id == _pol.ENH_HAMMER:
                        _counters['SELECTED_enh_hammer'] += 1
                    elif card.id == _pol.POKE_PAD:
                        _counters['SELECTED_poke_pad'] += 1
            elif o.type == OptionType.RETREAT:
                _counters['SELECTED_retreat'] += 1
            elif o.type == OptionType.ATTACK:
                _counters['SELECTED_attack'] += 1
            elif o.type == OptionType.EVOLVE:
                evo_card = _pol._get_card(obs, AreaType.HAND, o.index, my_idx)
                if evo_card:
                    if evo_card.id == _pol.KADABRA:
                        _counters['SELECTED_evolve_kadabra'] += 1
                    elif evo_card.id == _pol.ALAKAZAM:
                        _counters['SELECTED_evolve_alakazam'] += 1
                    elif evo_card.id == _pol.DUDUNSPARCE:
                        _counters['SELECTED_evolve_dudunsparce'] += 1
    return result


def _patched_handle_to_hand(obs, options, min_count, max_count):
    from cg.api import AreaType
    state  = obs.current
    my_idx = state.yourIndex
    field  = _pol._field_counts(state, my_idx)

    result = _orig_handle_to_hand(obs, options, min_count, max_count)
    chosen = set(result)
    for i, o in enumerate(options):
        if i in chosen:
            card = _pol._get_card(obs, o.area, o.index, my_idx)
            if card:
                if card.id == _pol.KADABRA:
                    if (field[_pol.ABRA] >= 1 and field[_pol.KADABRA] == 0
                            and field[_pol.ALAKAZAM] == 0):
                        _counters['SELECTED_v342_hilda_kadabra_priority'] += 1
                    else:
                        _counters['SELECTED_to_hand_kadabra_other'] += 1
    return result


def _patched_handle_attach_to(obs, options, min_count, max_count):
    from cg.api import AreaType
    state  = obs.current
    my_idx = state.yourIndex
    op_state = state.players[1 - my_idx]
    blocker_present = _pol.has_damage_blocker_revealed(op_state)

    for o in options:
        area  = o.inPlayArea if hasattr(o, 'inPlayArea') else AreaType.BENCH
        index = o.inPlayIndex if hasattr(o, 'inPlayIndex') else o.index
        poke  = _pol._get_card(obs, area, index, my_idx)
        if poke and poke.id == _pol.LILLIE_CLEFAIRY_EX:
            _counters['EVALUATED_v343_clefairy_energy'] += 1
            if blocker_present and _pol._energy_count(poke) < 2:
                _counters['FIRED_v343_clefairy_proactive'] += 1

    result = _orig_handle_attach_to(obs, options, min_count, max_count)
    return result


_pol.handle_main      = _patched_handle_main
_pol.handle_to_hand   = _patched_handle_to_hand
_pol.handle_attach_to = _patched_handle_attach_to

# ── Run N games ──────────────────────────────────────────────────────────────
import importlib.util
spec = importlib.util.spec_from_file_location("main", "agent/main.py")
mod  = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
agent_fn = mod.agent

from kaggle_environments import make

NUM_GAMES = int(sys.argv[1]) if len(sys.argv) > 1 else 20
print(f"Running {NUM_GAMES} games for fire-count audit v2...\n")
t0 = time.time()

for i in range(1, NUM_GAMES + 1):
    _current_game[0] = i
    _current_turn[0] = 0
    _turn_candy_condition[0] = False
    _turn_candy_played[0] = False
    try:
        env = make("cabt")
        env.run([agent_fn, agent_fn])
        _flush_turn()  # flush final turn
        print(f"  Game {i}: done")
    except Exception as e:
        print(f"  Game {i}: ERROR — {e}")

elapsed = time.time() - t0

# ── Per-turn Rare Candy stats ────────────────────────────────────────────────
turns_with_condition = sum(1 for played in _candy_turns.values() if played is not None)
turns_candy_played   = sum(1 for played in _candy_turns.values() if played)
pct = (turns_candy_played / turns_with_condition * 100) if turns_with_condition > 0 else 0.0

print(f"\nCompleted {NUM_GAMES} games in {elapsed:.1f}s\n")
print("=" * 68)
print("FIRE-COUNT AUDIT v2 RESULTS")
print("=" * 68)

groups = {}
for k, v in sorted(_counters.items()):
    prefix = k.split('_')[0]
    groups.setdefault(prefix, []).append((k, v))

for prefix in ['EVALUATED', 'FIRED', 'SELECTED']:
    if prefix in groups:
        print(f"\n  [{prefix}]")
        for k, v in groups[prefix]:
            print(f"    {k:60s} {v:>6}")

print(f"\n  [PER-TURN RARE CANDY]")
print(f"    Turns where condition held (any eval)     : {turns_with_condition}")
print(f"    Turns Rare Candy actually played by EOT   : {turns_candy_played}")
print(f"    Per-turn conversion rate                  : {pct:.1f}%")
print("\n" + "=" * 68)
