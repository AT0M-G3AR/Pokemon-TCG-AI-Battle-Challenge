import json, sys, os
sys.path.insert(0, os.path.abspath('agent'))
from cg.api import to_observation_class, SelectContext, OptionType
import policy

intercepted_scores = []
old_pick_best = policy._pick_best
def capture_scores(scores, min_c, max_c, allow_empty=False):
    global intercepted_scores
    intercepted_scores = list(scores)
    return old_pick_best(scores, min_c, max_c, allow_empty)
policy._pick_best = capture_scores

with open('/Users/garygonzalez/Downloads/87115524.json', 'r') as f:
    replay = json.load(f)

for step_idx, step in enumerate(replay['steps']):
    for p_idx, player_data in enumerate(step):
        if player_data['observation'].get('step', -1) == 82:
            obs_dict = player_data['observation']
            obs = to_observation_class(obs_dict)
            if not obs.current: continue
            my_idx = obs.current.yourIndex
            
            print(f"\nPlayer_data idx {p_idx}, agent believes it is Player {my_idx} turn at step {obs_dict['step']}")
            
            hand_cards = [policy._get_card(obs, policy.AreaType.HAND, i, my_idx).id for i in range(len(obs.current.players[my_idx].hand))]
            print(f"Hand: {hand_cards}")
            
            if obs.select.context == SelectContext.MAIN:
                policy.handle_main(obs, obs.select.option, 1, 1)
                
                for i, o in enumerate(obs.select.option):
                    score = intercepted_scores[i] if i < len(intercepted_scores) else 'N/A'
                    desc = str(o.type)
                    if o.type == OptionType.PLAY:
                        card = policy._get_card(obs, policy.AreaType.HAND, o.index, my_idx)
                        desc = f"PLAY_CARD {card.id if card else 'None'}"
                    elif o.type == OptionType.ATTACK:
                        desc = f"ATTACK target={getattr(o, 'target', '')}"
                    elif o.type == OptionType.ABILITY:
                        poke = policy._get_card(obs, getattr(o, 'area', getattr(o, 'inPlayArea', policy.AreaType.BENCH)), o.index, my_idx)
                        desc = f"ABILITY from {poke.id if poke else 'None'}"
                    
                    print(f"Option {i}: {desc} -> Score: {score}")
