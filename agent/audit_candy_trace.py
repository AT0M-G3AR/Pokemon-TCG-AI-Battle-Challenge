"""
Trace a single missed-Candy turn in full detail.
Records every handle_main call in sequence when the Candy condition holds,
to understand the exact action sequence.
"""
import sys, os, time
from collections import defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'agent'))

import policy as _pol

_orig_handle_main = _pol.handle_main

_current_game = [0]
_current_turn = [0]
# Collect full traces for missed turns
_missed_traces = []
_current_trace = []
_candy_condition_this_turn = [False]
_candy_played_this_turn = [False]

def _new_turn():
    if _candy_condition_this_turn[0] and not _candy_played_this_turn[0] and _current_trace:
        _missed_traces.append(list(_current_trace))
        if len(_missed_traces) >= 5:  # Enough samples
            return
    _current_trace.clear()
    _candy_condition_this_turn[0] = False
    _candy_played_this_turn[0] = False

def _patched_handle_main(obs, options, min_count, max_count):
    from cg.api import OptionType, AreaType

    state    = obs.current
    my_idx   = state.yourIndex
    my_state = state.players[my_idx]
    field    = _pol._field_counts(state, my_idx)
    hand     = _pol._hand_counts(state, my_idx)
    active   = my_state.active[0] if my_state.active else None

    has_end = any(o.type == OptionType.END for o in options)
    if has_end:
        _new_turn()
        _current_turn[0] += 1

    candy_in_options = False
    candy_condition = False
    for o in options:
        if o.type == OptionType.PLAY:
            card = _pol._get_card(obs, AreaType.HAND, o.index, my_idx)
            if card and card.id == _pol.RARE_CANDY:
                candy_in_options = True
                if (field[_pol.ABRA] > 0 and hand[_pol.ALAKAZAM] > 0
                        and field[_pol.KADABRA] == 0):
                    candy_condition = True
                    _candy_condition_this_turn[0] = True

    result = _orig_handle_main(obs, options, min_count, max_count)

    chosen = set(result)
    if candy_condition:
        for i, o in enumerate(options):
            if i in chosen:
                if o.type == OptionType.PLAY:
                    card = _pol._get_card(obs, AreaType.HAND, o.index, my_idx)
                    action = f"PLAY:{card.id if card else '?'}"
                    if card and card.id == _pol.RARE_CANDY:
                        action = "PLAY:RARE_CANDY ✅"
                        _candy_played_this_turn[0] = True
                elif o.type == OptionType.EVOLVE:
                    card = _pol._get_card(obs, AreaType.HAND, o.index, my_idx)
                    action = f"EVOLVE:{card.id if card else '?'}"
                elif o.type == OptionType.ABILITY:
                    card = _pol._get_card(obs, AreaType.BENCH, o.index, my_idx)
                    if not card:
                        card = _pol._get_card(obs, AreaType.ACTIVE, o.index, my_idx)
                    action = f"ABILITY:{card.id if card else '?'}"
                elif o.type == OptionType.ATTACK:
                    op_state = state.players[1 - my_idx]
                    op_active = op_state.active[0] if op_state.active else None
                    op_hp = _pol._hp_remaining(op_active) if op_active else 999
                    hand_size = len(my_state.hand)
                    action = f"ATTACK (hand={hand_size}, dmg={hand_size*20}, op_hp={op_hp})"
                elif o.type == OptionType.END:
                    action = "END"
                else:
                    action = f"OTHER:{o.type}"

                _current_trace.append(action)

    return result


_pol.handle_main = _patched_handle_main

import importlib.util
spec = importlib.util.spec_from_file_location("main", "agent/main.py")
mod  = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
agent_fn = mod.agent

from kaggle_environments import make

NUM_GAMES = int(sys.argv[1]) if len(sys.argv) > 1 else 50
print(f"Running up to {NUM_GAMES} games, collecting 5 missed-Candy traces...\n")
t0 = time.time()

for i in range(1, NUM_GAMES + 1):
    if len(_missed_traces) >= 5:
        break
    _current_game[0] = i
    _current_turn[0] = 0
    _current_trace.clear()
    _candy_condition_this_turn[0] = False
    _candy_played_this_turn[0] = False
    try:
        env = make("cabt")
        env.run([agent_fn, agent_fn])
        # Flush final turn
        _new_turn()
    except Exception as e:
        print(f"  Game {i}: ERROR — {e}")

elapsed = time.time() - t0
print(f"Ran {_current_game[0]} games in {elapsed:.1f}s\n")
print("=" * 70)
print("MISSED-CANDY TURN ACTION SEQUENCES")
print("=" * 70)
for j, trace in enumerate(_missed_traces):
    print(f"\n  Missed turn #{j+1}:")
    for step, action in enumerate(trace):
        print(f"    Step {step+1}: {action}")
print("=" * 70)
