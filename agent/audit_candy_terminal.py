"""
Step 1 — Terminal-action analysis for Rare Candy missed turns.

For each turn where the Rare Candy condition held and Candy was NOT played,
record the TERMINAL action (the one that actually ended the turn), plus:
  - hand size at terminal action
  - active Pokémon ID
  - whether the terminal action was an attack (turn-ending)
  - projected damage if Alakazam attacked
  - opponent active HP remaining
  - whether Candy was "correct hold" (damage - 40 would drop below lethal)
"""
import sys, os, time
from collections import defaultdict, Counter

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'agent'))

import policy as _pol

_orig_handle_main = _pol.handle_main

_current_game = [0]
_current_turn = [0]
_missed_turns = []   # list of dicts, one per missed turn

# Per-turn state
_turn = {}

def _reset_turn():
    _turn.clear()
    _turn.update({
        'game': _current_game[0],
        'turn': _current_turn[0],
        'candy_condition_ever': False,
        'candy_played': False,
        'terminal_type': None,
        'terminal_hand_size': None,
        'terminal_active_id': None,
        'terminal_op_hp': None,
        'terminal_dmg_if_attack': None,
        'correct_hold': None,
        'all_terminals': [],   # all turn-ending actions with context
    })

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
    hand_size = len(my_state.hand)

    has_end = any(o.type == OptionType.END for o in options)
    if has_end:
        # New turn starting — flush previous
        if _turn.get('candy_condition_ever') and not _turn.get('candy_played'):
            _missed_turns.append(dict(_turn))
        _current_turn[0] += 1
        _reset_turn()

    # Check Rare Candy condition
    for o in options:
        if o.type == OptionType.PLAY:
            card = _pol._get_card(obs, AreaType.HAND, o.index, my_idx)
            if card and card.id == _pol.RARE_CANDY:
                if (field[_pol.ABRA] > 0 and hand[_pol.ALAKAZAM] > 0
                        and field[_pol.KADABRA] == 0):
                    _turn['candy_condition_ever'] = True

    result = _orig_handle_main(obs, options, min_count, max_count)

    chosen = set(result)
    for i, o in enumerate(options):
        if i in chosen:
            # Determine if this is a turn-ending action
            is_terminal = o.type in (OptionType.ATTACK, OptionType.END)
            if is_terminal:
                op_hp = _pol._hp_remaining(op_active) if op_active else 999
                dmg = hand_size * 20 if (active and active.id == _pol.ALAKAZAM) else 0
                dmg_after_candy = (hand_size - 2) * 20 if (active and active.id == _pol.ALAKAZAM) else 0

                # Correct hold = playing Candy would cost lethal on current target
                correct_hold = (
                    dmg >= op_hp  # current hand IS lethal
                    and dmg_after_candy < op_hp  # but post-Candy hand is NOT
                )

                entry = {
                    'type': str(o.type).split('.')[-1],
                    'hand_size': hand_size,
                    'active_id': active.id if active else None,
                    'op_hp': op_hp,
                    'dmg': dmg,
                    'dmg_after_candy': dmg_after_candy,
                    'correct_hold': correct_hold,
                }
                _turn['all_terminals'].append(entry)

                # The LAST terminal action in a turn is the actual turn-ender
                _turn['terminal_type'] = entry['type']
                _turn['terminal_hand_size'] = hand_size
                _turn['terminal_active_id'] = active.id if active else None
                _turn['terminal_op_hp'] = op_hp
                _turn['terminal_dmg_if_attack'] = dmg
                _turn['correct_hold'] = correct_hold

            if o.type == OptionType.PLAY:
                card = _pol._get_card(obs, AreaType.HAND, o.index, my_idx)
                if card and card.id == _pol.RARE_CANDY:
                    _turn['candy_played'] = True

    return result


_pol.handle_main = _patched_handle_main

import importlib.util
spec = importlib.util.spec_from_file_location("main", "agent/main.py")
mod  = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
agent_fn = mod.agent

from kaggle_environments import make

NUM_GAMES = int(sys.argv[1]) if len(sys.argv) > 1 else 30
print(f"Running {NUM_GAMES} games for terminal-action analysis...\n")
t0 = time.time()

_reset_turn()
for i in range(1, NUM_GAMES + 1):
    _current_game[0] = i
    _current_turn[0] = 0
    _reset_turn()
    try:
        env = make("cabt")
        env.run([agent_fn, agent_fn])
        # Flush final turn
        if _turn.get('candy_condition_ever') and not _turn.get('candy_played'):
            _missed_turns.append(dict(_turn))
        print(f"  Game {i}: done")
    except Exception as e:
        print(f"  Game {i}: ERROR — {e}")

elapsed = time.time() - t0

# ── Analysis ─────────────────────────────────────────────────────────────────
print(f"\nCompleted {NUM_GAMES} games in {elapsed:.1f}s\n")
print("=" * 72)
print("TERMINAL ACTION ANALYSIS — RARE CANDY MISSED TURNS")
print("=" * 72)
print(f"  Total missed turns collected: {len(_missed_turns)}\n")

# Classify each missed turn
genuinely_wrong = []
correct_holds   = []
no_terminal     = []

for t in _missed_turns:
    if t['terminal_type'] is None:
        no_terminal.append(t)
    elif t['correct_hold']:
        correct_holds.append(t)
    else:
        genuinely_wrong.append(t)

print(f"  Genuinely wrong (Candy should have played)  : {len(genuinely_wrong)}")
print(f"  Correct holds (Candy would cost lethal)     : {len(correct_holds)}")
print(f"  No terminal action recorded                 : {len(no_terminal)}")
print()

# Terminal breakdown for genuinely wrong turns
term_counter = Counter()
for t in genuinely_wrong:
    key = f"{t['terminal_type']} | active={t['terminal_active_id']} | hand={t['terminal_hand_size']}"
    term_counter[key] += 1

print("  Genuinely-wrong terminal actions:")
for k, v in term_counter.most_common():
    print(f"    {k:60s} {v:>4}")
print()

# Terminal breakdown for correct holds
term_counter2 = Counter()
for t in correct_holds:
    key = f"{t['terminal_type']} | active={t['terminal_active_id']} | hand={t['terminal_hand_size']} | dmg={t['terminal_dmg_if_attack']} | op_hp={t['terminal_op_hp']}"
    term_counter2[key] += 1

print("  Correct-hold terminal actions (sample, first 10):")
for k, v in list(term_counter2.most_common())[:10]:
    print(f"    {k:70s} {v:>4}")
print()

# Summary by terminal type
type_counter = Counter(t['terminal_type'] for t in genuinely_wrong if t['terminal_type'])
print("  Genuinely-wrong by terminal type:")
for k, v in type_counter.most_common():
    print(f"    {k:20s} {v:>4}")

print()
aktive_ids = Counter(t['terminal_active_id'] for t in genuinely_wrong if t['terminal_active_id'])
print("  Genuinely-wrong by active Pokémon ID:")
for k, v in aktive_ids.most_common():
    name_map = {743: 'Alakazam', 742: 'Kadabra', 741: 'Abra', 66: 'Dudunsparce', 65: 'Dunsparce'}
    print(f"    {name_map.get(k, str(k)):20s} (ID {k})   {v:>4}")

print("=" * 72)
