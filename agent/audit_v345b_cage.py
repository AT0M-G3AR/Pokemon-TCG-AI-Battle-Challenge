"""
v3.45b Batch audit:
1. Per-turn Cage sequencing — how often Cage played before attack on turns both were available
2. Bump-recovery fire count — how often a bumped Cage triggered the 10500 recovery priority
"""
import sys, os, time
sys.path.insert(0, os.path.abspath('.'))

import policy as pol
from cg.api import OptionType, AreaType, SelectContext
from kaggle_environments import make
import importlib.util

spec = importlib.util.spec_from_file_location('main_mod', 'main.py')
main_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(main_mod)
agent_fn = main_mod.agent

NUM_GAMES = 20

# ── Intercept infrastructure ─────────────────────────────────────────────────
cage_seq_turns     = []   # (turn_type, detail) per turn with both Cage + Attack available
bump_events        = []   # list of player_idx when a bump occurs
recovery_plays     = []   # list of (player_idx, score_at_play)
cage_plays_all     = []   # all Cage plays: (player_idx, score)

last_stadium       = [None, None]  # last seen stadium playerIndex per game turn
orig_handle_main   = pol.handle_main

def _stadium_player(state):
    st = getattr(state, 'stadium', None)
    return getattr(st, 'playerIndex', None) if st else None

def patched_handle_main(obs, options, min_count, max_count):
    state = obs.current
    my_idx = state.yourIndex
    op_idx = 1 - my_idx

    # ── Detect bump: opponent's stadium is now in play that wasn't before ──
    current_stadium_player = _stadium_player(state)
    prev_stadium_player = last_stadium[my_idx]
    last_stadium[my_idx] = current_stadium_player

    if (current_stadium_player == op_idx and prev_stadium_player != op_idx):
        bump_events.append({'player': my_idx, 'detail': f'opp_took_stadium'})

    # ── Identify what's in the options this turn ──
    cage_options = [
        o for o in options
        if o.type == OptionType.PLAY
        and pol._get_card(obs, AreaType.HAND, o.index, my_idx) is not None
        and pol._get_card(obs, AreaType.HAND, o.index, my_idx).id == pol.BATTLE_CAGE
    ]
    has_attack = any(o.type == OptionType.ATTACK for o in options)
    has_cage   = len(cage_options) > 0

    # Run the real scorer and capture scores
    from unittest.mock import patch

    score_map = {}
    orig_pick = pol._pick_best

    def recording_pick(scores_iter, mn, mx, **kw):
        scores_list = list(scores_iter)
        for i, s in enumerate(scores_list):
            score_map[i] = s
        return orig_pick(iter(scores_list), mn, mx, **kw)

    pol._pick_best = recording_pick
    result = orig_handle_main(obs, options, min_count, max_count)
    pol._pick_best = orig_pick

    # ── Classify if Cage+Attack were both on the menu ──
    if has_cage and has_attack:
        chosen = set(result)
        cage_chosen_idxs = [i for i, o in enumerate(options) if i in chosen and o.type == OptionType.PLAY
                            and pol._get_card(obs, AreaType.HAND, o.index, my_idx) is not None
                            and pol._get_card(obs, AreaType.HAND, o.index, my_idx).id == pol.BATTLE_CAGE]
        atk_chosen = any(options[i].type == OptionType.ATTACK for i in chosen)

        cage_score_val = score_map.get(
            next((i for i, o in enumerate(options) if o.type == OptionType.PLAY
                  and pol._get_card(obs, AreaType.HAND, o.index, my_idx) is not None
                  and pol._get_card(obs, AreaType.HAND, o.index, my_idx).id == pol.BATTLE_CAGE), -1),
            None
        )
        atk_score_val = score_map.get(
            next((i for i, o in enumerate(options) if o.type == OptionType.ATTACK), -1),
            None
        )

        if cage_chosen_idxs and not atk_chosen:
            cage_seq_turns.append(('CAGE_FIRST', f'cage_score={cage_score_val}, atk_score={atk_score_val}'))
        elif atk_chosen and not cage_chosen_idxs:
            cage_seq_turns.append(('ATK_FIRST', f'cage_score={cage_score_val}, atk_score={atk_score_val}'))
        else:
            cage_seq_turns.append(('BOTH_OR_NEITHER', f'chosen={chosen}'))

    # ── Track all Cage plays and recovery branch ──
    for i, o in enumerate(options):
        if i in set(result) and o.type == OptionType.PLAY:
            card = pol._get_card(obs, AreaType.HAND, o.index, my_idx)
            if card and card.id == pol.BATTLE_CAGE:
                sc = score_map.get(i, None)
                cage_plays_all.append({'player': my_idx, 'score': sc})
                if sc and sc >= 10500:
                    recovery_plays.append({'player': my_idx, 'score': sc})

    return result

pol.handle_main = patched_handle_main

# ── Run batch ────────────────────────────────────────────────────────────────
print(f"Running {NUM_GAMES} games for v3.45b bump-trace audit...")
t0 = time.time()
for g in range(NUM_GAMES):
    last_stadium[0] = last_stadium[1] = None
    env = make('cabt')
    env.run([agent_fn, agent_fn])
    print(f"  Game {g+1}: done")

elapsed = time.time() - t0
print(f"\nCompleted {NUM_GAMES} games in {elapsed:.1f}s\n")

# ── Report ────────────────────────────────────────────────────────────────────
print("=" * 66)
print("BATTLE CAGE SEQUENCING + BUMP-TRACE AUDIT")
print("=" * 66)

cage_first = sum(1 for t, _ in cage_seq_turns if t == 'CAGE_FIRST')
atk_first  = sum(1 for t, _ in cage_seq_turns if t == 'ATK_FIRST')
both_or_nei= sum(1 for t, _ in cage_seq_turns if t == 'BOTH_OR_NEITHER')
total_contested = len(cage_seq_turns)

print(f"\n[A] Per-turn sequencing (turns where BOTH Cage + Attack were options)")
print(f"    Total contested turns : {total_contested}")
print(f"    Cage played first     : {cage_first}  ({100*cage_first/max(total_contested,1):.0f}%)")
print(f"    Attack fired first    : {atk_first}   ({100*atk_first/max(total_contested,1):.0f}%)")
print(f"    Both/neither          : {both_or_nei}")
if atk_first > 0:
    print(f"\n    ATK_FIRST cases (up to 10):")
    shown = 0
    for t, detail in cage_seq_turns:
        if t == 'ATK_FIRST' and shown < 10:
            print(f"      {detail}")
            shown += 1

print(f"\n[B] Bump-recovery fire counts")
print(f"    Stadium bumps detected: {len(bump_events)}")
print(f"    All Cage plays        : {len(cage_plays_all)}")
print(f"      Scores: {sorted(set(p['score'] for p in cage_plays_all if p['score'] is not None))}")
print(f"    Recovery plays (score=10500): {len(recovery_plays)}")
if len(bump_events) > 0 and len(recovery_plays) == 0:
    print(f"\n    ⚠️  BUMPS OCCURRED but 0 recovery plays — check playerIndex detection")
elif len(bump_events) == 0:
    print(f"\n    NOTE: Mirror game — bump detection depends on playerIndex attribute")
    print(f"    Check if 'stadium' attribute exposes playerIndex in the game state.")

print(f"\n{'=' * 66}")
