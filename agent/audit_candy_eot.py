"""
Rare Candy EOT miss analysis:
For turns where the condition held AND Rare Candy was NOT played,
was the Rare Candy OPTION even present in the FINAL handle_main call
(the one that chose ATTACK or EVOLVE:Dudunsparce)?

This distinguishes:
  A) "Played something better first, Rare Candy was gone from hand" → correct
  B) "Rare Candy still in hand at EOT but something else outscored it" → potential bug
"""
import sys, os, time
from collections import defaultdict, Counter

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'agent'))

import policy as _pol

_orig_handle_main = _pol.handle_main

_current_game = [0]
_current_turn = [0]
_turn_state = {}

def _turn_key():
    return (_current_game[0], _current_turn[0])

def _ensure_turn():
    k = _turn_key()
    if k not in _turn_state:
        _turn_state[k] = {
            'candy_condition_ever': False,
            'candy_played': False,
            'final_selection_with_candy_available': None,
        }
    return _turn_state[k]

def _patched_handle_main(obs, options, min_count, max_count):
    from cg.api import OptionType, AreaType

    state    = obs.current
    my_idx   = state.yourIndex
    my_state = state.players[my_idx]
    field    = _pol._field_counts(state, my_idx)
    hand     = _pol._hand_counts(state, my_idx)

    has_end = any(o.type == OptionType.END for o in options)
    if has_end:
        _current_turn[0] += 1

    turn = _ensure_turn()

    candy_available_this_eval = False
    candy_condition_this_eval = False
    for o in options:
        if o.type == OptionType.PLAY:
            card = _pol._get_card(obs, AreaType.HAND, o.index, my_idx)
            if card and card.id == _pol.RARE_CANDY:
                candy_available_this_eval = True
                if (field[_pol.ABRA] > 0 and hand[_pol.ALAKAZAM] > 0
                        and field[_pol.KADABRA] == 0):
                    candy_condition_this_eval = True
                    turn['candy_condition_ever'] = True

    result = _orig_handle_main(obs, options, min_count, max_count)

    chosen = set(result)
    for i, o in enumerate(options):
        if i in chosen:
            if candy_condition_this_eval:
                if o.type == OptionType.PLAY:
                    card = _pol._get_card(obs, AreaType.HAND, o.index, my_idx)
                    if card and card.id == _pol.RARE_CANDY:
                        turn['candy_played'] = True
                        turn['final_selection_with_candy_available'] = 'PLAY:RARE_CANDY'
                    else:
                        name = f"PLAY:{card.id}" if card else "PLAY:?"
                        turn['final_selection_with_candy_available'] = name
                elif o.type == OptionType.EVOLVE:
                    card = _pol._get_card(obs, AreaType.HAND, o.index, my_idx)
                    cid = card.id if card else '?'
                    if candy_available_this_eval:
                        turn['final_selection_with_candy_available'] = f"EVOLVE:{cid}_candy_still_in_hand"
                    else:
                        turn['final_selection_with_candy_available'] = f"EVOLVE:{cid}_candy_gone"
                elif o.type == OptionType.ABILITY:
                    card = _pol._get_card(obs, AreaType.BENCH, o.index, my_idx)
                    if not card:
                        card = _pol._get_card(obs, AreaType.ACTIVE, o.index, my_idx)
                    cid = card.id if card else '?'
                    if candy_available_this_eval:
                        turn['final_selection_with_candy_available'] = f"ABILITY:{cid}_candy_still_in_hand"
                    else:
                        turn['final_selection_with_candy_available'] = f"ABILITY:{cid}_candy_gone"
                elif o.type == OptionType.ATTACK:
                    if candy_available_this_eval:
                        turn['final_selection_with_candy_available'] = "ATTACK_candy_still_in_hand"
                    else:
                        turn['final_selection_with_candy_available'] = "ATTACK_candy_gone"
                elif o.type == OptionType.END:
                    turn['final_selection_with_candy_available'] = "END"
                else:
                    turn['final_selection_with_candy_available'] = f"OTHER:{o.type}"
    return result

_pol.handle_main = _patched_handle_main

import importlib.util
spec = importlib.util.spec_from_file_location("main", "agent/main.py")
mod  = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
agent_fn = mod.agent

from kaggle_environments import make

NUM_GAMES = int(sys.argv[1]) if len(sys.argv) > 1 else 20
print(f"Running {NUM_GAMES} games...\n")
t0 = time.time()

for i in range(1, NUM_GAMES + 1):
    _current_game[0] = i
    _current_turn[0] = 0
    try:
        env = make("cabt")
        env.run([agent_fn, agent_fn])
        print(f"  Game {i}: done")
    except Exception as e:
        print(f"  Game {i}: ERROR — {e}")

elapsed = time.time() - t0

turns_with_condition = {k: v for k, v in _turn_state.items() if v['candy_condition_ever']}
turns_played = {k: v for k, v in turns_with_condition.items() if v['candy_played']}
turns_not_played = {k: v for k, v in turns_with_condition.items() if not v['candy_played']}

final_sel_counts = Counter(
    v['final_selection_with_candy_available']
    for v in turns_not_played.values()
    if v['final_selection_with_candy_available']
)

print(f"\nCompleted {NUM_GAMES} games in {elapsed:.1f}s\n")
print("=" * 70)
print("RARE CANDY EOT MISS — FINAL SELECTION BREAKDOWN")
print("=" * 70)
print(f"  Turns with condition           : {len(turns_with_condition)}")
print(f"  Played                         : {len(turns_played)}")
print(f"  Not played                     : {len(turns_not_played)}")
print()
print("  Final action on turns where candy NOT played:")
for sel, count in final_sel_counts.most_common():
    flag = " 🔴 BUG?" if "candy_still_in_hand" in sel and "ATTACK" in sel else ""
    flag = flag or (" 🔴 BUG?" if "candy_still_in_hand" in sel and "EVOLVE:66" in sel else "")
    print(f"    {sel:60s} {count:>5}{flag}")
print("=" * 70)
