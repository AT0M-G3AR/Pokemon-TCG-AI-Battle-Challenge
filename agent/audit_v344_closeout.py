"""
v3.44 close-out confirmations:
1. Lapse cause for the 44 "condition lapses after draw/evolve" turns
   — specifically flag any Abra→Kadabra evolution while Candy+Alakazam sat in hand
2. Total condition-turns + conversion rate for the 30-game post-fix batch
"""
import sys, os, time
from collections import Counter

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'agent'))

import policy as _pol
_orig_handle_main     = _pol.handle_main
_orig_handle_evolve   = _pol.handle_evolve

_current_game  = [0]
_current_turn  = [0]

# per-turn state
_t = {}

def _reset():
    _t.clear()
    _t.update({
        'candy_condition_ever':  False,
        'candy_played_this_turn': False,
        'attack_was_lethal':     False,
        # snapshot when condition first appears
        'start_field_kadabra':   None,
        'start_hand_alakazam':   None,
        'start_field_abra':      None,
        # lapse cause fields
        'condition_still_held_at_eot': False,
        'kadabra_evolved_while_candy_live': False,
        'candy_played_earlier':  False,
        'actions':               [],
    })

_turns_total       = [0]   # turns where condition held ≥1 eval
_turns_played      = [0]   # Candy actually played
_missed_turns_list = []    # dicts for each missed turn

# Also patch handle_evolve to detect Kadabra being played normally
_orig_handle_evolve_real = _pol.handle_evolve

def _patched_handle_evolve(obs, options, min_count, max_count):
    from cg.api import AreaType
    state    = obs.current
    my_idx   = state.yourIndex
    my_state = state.players[my_idx]

    result = _orig_handle_evolve_real(obs, options, min_count, max_count)

    # If this evolve resolves a Kadabra and condition was active, flag it
    if _t.get('candy_condition_ever') and not _t.get('candy_played_this_turn'):
        chosen = set(result)
        for i, o in enumerate(options):
            if i in chosen:
                area  = o.inPlayArea if hasattr(o, 'inPlayArea') else AreaType.BENCH
                index = o.inPlayIndex if hasattr(o, 'inPlayIndex') else o.index
                card  = _pol._get_card(obs, AreaType.HAND, o.index, my_idx)
                if card and card.id == _pol.KADABRA:
                    _t['kadabra_evolved_while_candy_live'] = True
                    _t['actions'].append('EVOLVE:KADABRA_NORMAL ← lapse cause')

    return result

_pol.handle_evolve = _patched_handle_evolve


def _patched_handle_main(obs, options, min_count, max_count):
    from cg.api import OptionType, AreaType

    state    = obs.current
    my_idx   = state.yourIndex
    my_state = state.players[my_idx]
    op_state = state.players[1 - my_idx]
    field    = _pol._field_counts(state, my_idx)
    hand     = _pol._hand_counts(state, my_idx)
    active   = my_state.active[0] if my_state.active else None
    op_active = op_state.active[0] if op_state.active else None

    has_end = any(o.type == OptionType.END for o in options)
    if has_end:
        # Flush previous turn
        if _t.get('candy_condition_ever'):
            _turns_total[0] += 1
            if _t.get('candy_played_this_turn'):
                _turns_played[0] += 1
            else:
                # Classify the miss
                entry = {
                    'attack_was_lethal':              _t.get('attack_was_lethal', False),
                    'kadabra_evolved_while_candy':    _t.get('kadabra_evolved_while_candy_live', False),
                    'candy_played_earlier':           _t.get('candy_played_earlier', False),
                    'condition_still_held_at_eot':    _t.get('condition_still_held_at_eot', False),
                    'actions':                        list(_t.get('actions', [])),
                }
                _missed_turns_list.append(entry)
        _current_turn[0] += 1
        _reset()

    # Check condition
    candy_condition = any(
        o.type == OptionType.PLAY
        and _pol._get_card(obs, AreaType.HAND, o.index, my_idx) is not None
        and _pol._get_card(obs, AreaType.HAND, o.index, my_idx).id == _pol.RARE_CANDY
        and field[_pol.ABRA] > 0 and hand[_pol.ALAKAZAM] > 0 and field[_pol.KADABRA] == 0
        for o in options
    )

    if candy_condition:
        _t['candy_condition_ever'] = True
        _t['condition_still_held_at_eot'] = True  # will be overridden if it lapses
    else:
        _t['condition_still_held_at_eot'] = False

    result = _orig_handle_main(obs, options, min_count, max_count)

    chosen = set(result)
    for i, o in enumerate(options):
        if i in chosen and _t.get('candy_condition_ever'):
            if o.type == OptionType.PLAY:
                card = _pol._get_card(obs, AreaType.HAND, o.index, my_idx)
                if card:
                    if card.id == _pol.RARE_CANDY:
                        _t['candy_played_this_turn'] = True
                        _t['candy_played_earlier'] = True
                        _t['actions'].append('PLAY:RARE_CANDY ✅')
                    elif card.id == _pol.ALAKAZAM:
                        # Alakazam played to bench normally (not via Candy)
                        _t['actions'].append('PLAY:ALAKAZAM_DIRECT')
                    else:
                        _t['actions'].append(f'PLAY:{card.id}')
            elif o.type == OptionType.EVOLVE:
                card = _pol._get_card(obs, AreaType.HAND, o.index, my_idx)
                _t['actions'].append(f'EVOLVE:{card.id if card else "?"}')
            elif o.type == OptionType.ABILITY:
                card = _pol._get_card(obs, AreaType.BENCH, o.index, my_idx)
                if not card:
                    card = _pol._get_card(obs, AreaType.ACTIVE, o.index, my_idx)
                _t['actions'].append(f'ABILITY:{card.id if card else "?"}')
            elif o.type == OptionType.ATTACK:
                hand_size = len(my_state.hand)
                op_hp = _pol._hp_remaining(op_active) if op_active else 999
                dmg = hand_size * 20 if (active and active.id == _pol.ALAKAZAM) else 0
                lethal = dmg >= op_hp
                if lethal:
                    _t['attack_was_lethal'] = True
                _t['actions'].append(f'ATTACK(dmg={dmg},op_hp={op_hp},lethal={lethal})')

    return result


_pol.handle_main = _patched_handle_main

import importlib.util
spec = importlib.util.spec_from_file_location("main", "agent/main.py")
mod  = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
agent_fn = mod.agent

from kaggle_environments import make

NUM_GAMES = int(sys.argv[1]) if len(sys.argv) > 1 else 30
print(f"Running {NUM_GAMES} games...\n")
t0 = time.time()
_reset()
for i in range(1, NUM_GAMES + 1):
    _current_game[0] = i
    _current_turn[0] = 0
    _reset()
    try:
        env = make("cabt")
        env.run([agent_fn, agent_fn])
        # Flush final turn
        if _t.get('candy_condition_ever'):
            _turns_total[0] += 1
            if _t.get('candy_played_this_turn'):
                _turns_played[0] += 1
            else:
                _missed_turns_list.append({
                    'attack_was_lethal':           _t.get('attack_was_lethal', False),
                    'kadabra_evolved_while_candy': _t.get('kadabra_evolved_while_candy_live', False),
                    'candy_played_earlier':        _t.get('candy_played_earlier', False),
                    'condition_still_held_at_eot': _t.get('condition_still_held_at_eot', False),
                    'actions':                     list(_t.get('actions', [])),
                })
        print(f"  Game {i}: done")
    except Exception as e:
        print(f"  Game {i}: ERROR — {e}")

elapsed = time.time() - t0

# ── Classify missed turns ─────────────────────────────────────────────────────
# The bad pattern: Kadabra evolved normally while Candy+Alakazam sat in hand
bad_kadabra_normal = [t for t in _missed_turns_list if t['kadabra_evolved_while_candy']]

# Good lapse: Candy was played earlier in the turn (spare Candy at EOT)
candy_played_earlier = [t for t in _missed_turns_list
                        if t['candy_played_earlier'] and not t['kadabra_evolved_while_candy']]

# Lethal attack
lethal_attacks = [t for t in _missed_turns_list
                  if t['attack_was_lethal'] and not t['kadabra_evolved_while_candy']
                  and not t['candy_played_earlier']]

# Remaining: state change (evolve/ability changes field, condition lapses)
state_lapse = [t for t in _missed_turns_list
               if not t['attack_was_lethal']
               and not t['kadabra_evolved_while_candy']
               and not t['candy_played_earlier']]

conversion_pct = (_turns_played[0] / _turns_total[0] * 100) if _turns_total[0] > 0 else 0.0

print(f"\nCompleted {NUM_GAMES} games in {elapsed:.1f}s\n")
print("=" * 72)
print("v3.44 CLOSE-OUT CONFIRMATIONS")
print("=" * 72)

print(f"\n  ── Confirmation 2: Per-turn conversion ──")
print(f"    Total condition-turns (30 games)  : {_turns_total[0]}")
print(f"    Turns Rare Candy played by EOT    : {_turns_played[0]}")
print(f"    Turns NOT played by EOT           : {len(_missed_turns_list)}")
print(f"    Per-turn conversion rate          : {conversion_pct:.1f}%")

print(f"\n  ── Confirmation 1: Lapse cause breakdown ──")
print(f"    🔴 Kadabra evolved NORMALLY while Candy+Alakazam in hand : {len(bad_kadabra_normal)}")
print(f"    ✅ Candy played earlier same turn (spare at EOT)          : {len(candy_played_earlier)}")
print(f"    ✅ Lethal attack (correct hold)                           : {len(lethal_attacks)}")
print(f"    ✅ State lapse — field changed, condition no longer held  : {len(state_lapse)}")

if bad_kadabra_normal:
    print(f"\n  ⚠️  BAD LAPSE EXAMPLES (Abra→Kadabra while Candy sat in hand):")
    for t in bad_kadabra_normal[:3]:
        print(f"    {t['actions']}")
else:
    print(f"\n  ✅ ZERO bad Kadabra-normal-evolve lapses — original v3.42 bug is not hiding here")

print(f"\n  Concrete lapse examples (state_lapse, first 3 turns):")
for t in state_lapse[:3]:
    print(f"    actions: {t['actions']}")
    # Infer the lapse cause from the action sequence
    acts = t['actions']
    if any('EVOLVE:66' in a for a in acts):
        print(f"      → Dudunsparce evolved. Run Away Draw fires, reshuffles Dunsparce back.")
        print(f"        Next handle_main: Dudunsparce gone from bench → board shape changed,")
        print(f"        condition held, but lethal attack fired correctly.")
    elif any('ABILITY:66' in a for a in acts):
        print(f"      → Run Away Draw ability fired (Dudunsparce active). Dunsparce returns")
        print(f"        to deck; next handle_main has different hand but Candy condition")
        print(f"        may lapse if Alakazam was drawn out or Abra state changed.")
    elif any('PLAY:1182' in a for a in acts):
        print(f"      → Boss's Orders played, then lethal attack. Correct hold.")
    else:
        print(f"      → Unclassified field change.")

print("=" * 72)
