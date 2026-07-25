"""
Rare Candy per-turn conversion deep dive.
For each turn where the condition held and Candy was NOT played:
log what was selected instead and what options were available.
"""
import sys, os, time, json
from collections import defaultdict, Counter

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'agent'))

import policy as _pol

_orig_handle_main = _pol.handle_main

# Turn tracking
_current_game = [0]
_current_turn = [0]
_turn_state = {}    # (game, turn) -> {'candy_condition': bool, 'candy_played': bool, 'winners': []}

def _turn_key():
    return (_current_game[0], _current_turn[0])

def _ensure_turn():
    k = _turn_key()
    if k not in _turn_state:
        _turn_state[k] = {'candy_condition': False, 'candy_played': False, 'winners': []}
    return _turn_state[k]

def _flush_turn():
    # nothing to do — all data is recorded inline
    pass

_orig_handle_main = _pol.handle_main

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

    # Check Rare Candy condition
    candy_condition_this_eval = False
    for o in options:
        if o.type == OptionType.PLAY:
            card = _pol._get_card(obs, AreaType.HAND, o.index, my_idx)
            if card and card.id == _pol.RARE_CANDY:
                if (field[_pol.ABRA] > 0 and hand[_pol.ALAKAZAM] > 0
                        and field[_pol.KADABRA] == 0):
                    candy_condition_this_eval = True
                    turn['candy_condition'] = True

    result = _orig_handle_main(obs, options, min_count, max_count)

    if candy_condition_this_eval:
        chosen = set(result)
        for i, o in enumerate(options):
            if i in chosen:
                if o.type == OptionType.PLAY:
                    card = _pol._get_card(obs, AreaType.HAND, o.index, my_idx)
                    winner = f"PLAY:{card.id}" if card else "PLAY:?"
                    if card and card.id == _pol.RARE_CANDY:
                        turn['candy_played'] = True
                        winner = "PLAY:RARE_CANDY"
                elif o.type == OptionType.ABILITY:
                    card = _pol._get_card(obs, AreaType.BENCH, o.index, my_idx)
                    if not card:
                        card = _pol._get_card(obs, AreaType.ACTIVE, o.index, my_idx)
                    winner = f"ABILITY:{card.id if card else '?'}"
                elif o.type == OptionType.EVOLVE:
                    card = _pol._get_card(obs, AreaType.HAND, o.index, my_idx)
                    winner = f"EVOLVE:{card.id if card else '?'}"
                elif o.type == OptionType.ATTACK:
                    winner = "ATTACK"
                elif o.type == OptionType.RETREAT:
                    winner = "RETREAT"
                elif o.type == OptionType.END:
                    winner = "END"
                else:
                    winner = f"OTHER:{o.type}"
                turn['winners'].append(winner)

    return result


_pol.handle_main = _patched_handle_main

import importlib.util
spec = importlib.util.spec_from_file_location("main", "agent/main.py")
mod  = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
agent_fn = mod.agent

from kaggle_environments import make

NUM_GAMES = int(sys.argv[1]) if len(sys.argv) > 1 else 20
print(f"Running {NUM_GAMES} games for Rare Candy deep dive...\n")
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

# Analysis
turns_with_condition = {k: v for k, v in _turn_state.items() if v['candy_condition']}
turns_played = {k: v for k, v in turns_with_condition.items() if v['candy_played']}
turns_not_played = {k: v for k, v in turns_with_condition.items() if not v['candy_played']}

winner_counts_when_unplayed = Counter()
for v in turns_not_played.values():
    for w in v['winners']:
        winner_counts_when_unplayed[w] += 1

print(f"\nCompleted {NUM_GAMES} games in {elapsed:.1f}s\n")
print("=" * 64)
print("RARE CANDY PER-TURN CONVERSION DEEP DIVE")
print("=" * 64)
print(f"  Turns where condition held (abra+ala in hand, no kad)  : {len(turns_with_condition)}")
print(f"  Turns Rare Candy played by EOT                         : {len(turns_played)}")
print(f"  Turns Rare Candy NOT played by EOT                     : {len(turns_not_played)}")
pct = len(turns_played) / len(turns_with_condition) * 100 if turns_with_condition else 0
print(f"  Per-turn conversion rate                               : {pct:.1f}%")
print()
print("  What won instead (when Rare Candy was NOT played):")
for winner, count in winner_counts_when_unplayed.most_common():
    print(f"    {winner:50s} {count:>6}")
print("=" * 64)
