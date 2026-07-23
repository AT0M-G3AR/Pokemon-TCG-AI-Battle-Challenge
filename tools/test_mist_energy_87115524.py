import sys, json, os
sys.path.insert(0, 'agent')
import policy
from cg.api import to_observation_class, OptionType, all_card_data

cards = {c.cardId: c.name for c in all_card_data()}

captured = {}
_orig_pb = policy._pick_best
def hooked(s, mn, mx): captured['scores'] = list(s); return _orig_pb(s, mn, mx)
policy._pick_best = hooked

with open('87115524.json') as f:
    replay = json.load(f)

step_idx = 82
slot = 0
step = replay['steps'][step_idx]
if len(step) > slot:
    entry = step[slot]
    obs_dict = entry.get('observation', {})
    opts = obs_dict.get('select', {}).get('option', [])
    obs = to_observation_class(obs_dict)
    
    result = policy.select_action(obs)
    scores = captured.get('scores', [])
    
    print(f"\n=== Step {step_idx} ===")
    paired = sorted(zip(scores, [o.get('type') for o in opts], range(len(opts))), reverse=True)
    for s, t, i in paired[:10]:
        try: tname = OptionType(t).name
        except: tname = f'type={t}'
        print(f"  [{i:>2}] {tname:12s} score={s:>10.1f}")
else:
    print("Step 82 slot 0 not found")
