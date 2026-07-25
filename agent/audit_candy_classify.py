"""
Classification audit: Are the remaining 'not played' turns actually correct holds?
Classify each missed turn as:
  - CORRECT_LETHAL: attack on that turn was lethal (dmg >= op_hp) → correct not to play Candy
  - CORRECT_EVOLVE_THEN_STATE_CHANGE: Dudunsparce evolve was the only action → condition lapsed
  - WRONG: Candy still in hand, attack non-lethal, no valid reason to skip
"""
import sys, os, time
from collections import Counter

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'agent'))

import policy as _pol

_orig_handle_main = _pol.handle_main

_current_game = [0]
_current_turn = [0]

# Per-turn tracking
_turn = {
    'candy_condition_ever': False,
    'candy_played': False,
    'attack_was_lethal': False,
    'actions_while_candy_live': [],
}

def _reset_turn():
    _turn['candy_condition_ever'] = False
    _turn['candy_played'] = False
    _turn['attack_was_lethal'] = False
    _turn['actions_while_candy_live'] = []

_missed = []  # list of dicts

def _flush_turn():
    if _turn['candy_condition_ever'] and not _turn['candy_played']:
        _missed.append({
            'attack_was_lethal': _turn['attack_was_lethal'],
            'actions': list(_turn['actions_while_candy_live']),
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

    has_end = any(o.type == OptionType.END for o in options)
    if has_end:
        _flush_turn()
        _current_turn[0] += 1
        _reset_turn()

    candy_condition = any(
        o.type == OptionType.PLAY
        and _pol._get_card(obs, AreaType.HAND, o.index, my_idx) is not None
        and _pol._get_card(obs, AreaType.HAND, o.index, my_idx).id == _pol.RARE_CANDY
        and field[_pol.ABRA] > 0 and hand[_pol.ALAKAZAM] > 0 and field[_pol.KADABRA] == 0
        for o in options
    )
    if candy_condition:
        _turn['candy_condition_ever'] = True

    result = _orig_handle_main(obs, options, min_count, max_count)

    chosen = set(result)
    for i, o in enumerate(options):
        if i in chosen and _turn['candy_condition_ever']:
            if o.type == OptionType.PLAY:
                card = _pol._get_card(obs, AreaType.HAND, o.index, my_idx)
                if card and card.id == _pol.RARE_CANDY:
                    _turn['candy_played'] = True
                if card:
                    _turn['actions_while_candy_live'].append(f'PLAY:{card.id}')
            elif o.type == OptionType.ATTACK:
                hand_size = len(my_state.hand)
                op_hp = _pol._hp_remaining(op_active) if op_active else 999
                dmg = hand_size * 20 if (active and active.id == _pol.ALAKAZAM) else 0
                lethal = dmg >= op_hp
                if lethal:
                    _turn['attack_was_lethal'] = True
                _turn['actions_while_candy_live'].append(f'ATTACK(dmg={dmg},op_hp={op_hp},lethal={lethal})')
            elif o.type == OptionType.EVOLVE:
                card = _pol._get_card(obs, AreaType.HAND, o.index, my_idx)
                _turn['actions_while_candy_live'].append(f'EVOLVE:{card.id if card else "?"}')
            elif o.type == OptionType.ABILITY:
                card = _pol._get_card(obs, AreaType.BENCH, o.index, my_idx)
                if not card:
                    card = _pol._get_card(obs, AreaType.ACTIVE, o.index, my_idx)
                _turn['actions_while_candy_live'].append(f'ABILITY:{card.id if card else "?"}')

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
_reset_turn()
for i in range(1, NUM_GAMES + 1):
    _current_game[0] = i
    _current_turn[0] = 0
    _reset_turn()
    try:
        env = make("cabt")
        env.run([agent_fn, agent_fn])
        _flush_turn()
        print(f"  Game {i}: done")
    except Exception as e:
        print(f"  Game {i}: ERROR — {e}")

elapsed = time.time() - t0

correct_lethal = [t for t in _missed if t['attack_was_lethal']]
state_change   = [t for t in _missed if not t['attack_was_lethal'] and
                  all('EVOLVE:66' in a or 'ABILITY' in a for a in t['actions'])]
wrong          = [t for t in _missed if not t['attack_was_lethal'] and
                  any('ATTACK' in a and 'lethal=False' in a for a in t['actions'])]
other          = [t for t in _missed if t not in correct_lethal
                  and t not in state_change and t not in wrong]

print(f"\nCompleted {NUM_GAMES} games in {elapsed:.1f}s\n")
print("=" * 68)
print("CANDY MISS CLASSIFICATION")
print("=" * 68)
print(f"  Total missed turns: {len(_missed)}")
print(f"  CORRECT — lethal attack fired (Candy would cost nothing but wasn't needed): {len(correct_lethal)}")
print(f"  CORRECT — evolve/ability, condition lapsed next call                      : {len(state_change)}")
print(f"  WRONG   — non-lethal attack fired with Candy still in hand                : {len(wrong)}")
print(f"  OTHER   — unclassified                                                    : {len(other)}")
print()
print("  Sample WRONG turns (first 5):")
for t in wrong[:5]:
    print(f"    {t['actions']}")
print()
print("  Sample OTHER turns (first 5):")
for t in other[:5]:
    print(f"    {t['actions']}")
print("=" * 68)
