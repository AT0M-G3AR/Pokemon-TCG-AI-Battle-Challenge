import sys
import json
import os
import ctypes
sys.path.insert(0, 'agent')
from cg.api import to_observation_class, search_begin, search_step, search_release, OptionType, SelectContext, all_card_data

with open('/Users/garygonzalez/Downloads/86596187.json') as f:
    replay = json.load(f)

obs_dict = replay['steps'][58][1].get('observation')
obs = to_observation_class(obs_dict)

def evaluate_position(search_state):
    my_idx = search_state.observation.current.yourIndex
    my_state = search_state.observation.current.players[my_idx]
    opp_state = search_state.observation.current.players[1 - my_idx]
    hand_size = len(my_state.hand) if my_state.hand else 0
    opp_active = next((p for p in opp_state.active if p), None)
    opp_hp_left = opp_active.hp if opp_active else 0
    my_prizes = len([p for p in my_state.prize if p])
    opp_prizes = len([p for p in opp_state.prize if p])
    bench_count = len([p for p in my_state.bench if p])
    
    score = 0.0
    score -= opp_prizes * 10000
    score += my_prizes * 10000
    score -= opp_hp_left * 10
    score += hand_size * 50
    score += bench_count * 20
    return score

my_state = obs.current.players[obs.current.yourIndex]
opp_state = obs.current.players[1 - obs.current.yourIndex]

my_deck = [p.id for p in my_state.deck] if hasattr(my_state, 'deck') and my_state.deck else [1]*my_state.deckCount
my_prize = [1]*6
opp_deck = [1]*opp_state.deckCount
opp_prize = [1]*6
opp_hand = [1]*opp_state.handCount
opp_active = []
if opp_state.active and opp_state.active[0] is None:
    opp_active = [1] 

CARD_DB = {c.cardId: c for c in all_card_data()}
def get_card_name(cid):
    if not cid: return "None"
    return CARD_DB.get(cid).name if cid in CARD_DB else str(cid)

def simulate_forward(search_state, action_idx, max_chained=5):
    current_state = search_state
    try:
        current_state = search_step(current_state.searchId, [action_idx])
        chained = 1
        while current_state.observation.select and current_state.observation.select.context != SelectContext.MAIN:
            if chained >= max_chained or not current_state.observation.select.option:
                break
            current_state = search_step(current_state.searchId, [0])
            chained += 1
            
        if current_state.observation.select and current_state.observation.select.context == SelectContext.MAIN:
            attack_idx = -1
            for i, opt in enumerate(current_state.observation.select.option):
                if opt.type == OptionType.ATTACK:
                    attack_idx = i
                    break
            if attack_idx >= 0:
                current_state = search_step(current_state.searchId, [attack_idx])
    except Exception as e:
        print(f"  Simulate error: {e}")
    return current_state

search_state = search_begin(obs, my_deck, my_prize, opp_deck, opp_prize, opp_hand, opp_active)
options = search_state.observation.select.option
for i, opt in enumerate(options):
    cname = "Unknown"
    if opt.type == OptionType.PLAY and opt.index < len(my_state.hand):
        cname = get_card_name(my_state.hand[opt.index].id)
    elif opt.type == OptionType.EVOLVE:
        cname = "Evolve"
    elif opt.type == OptionType.ATTACK:
        cname = "Attack"
    
    if cname in ["Dawn", "Evolve", "Attack"]:
        print(f"\nSimulating {cname} (index {i})")
        sub_search = search_begin(obs, my_deck, my_prize, opp_deck, opp_prize, opp_hand, opp_active)
        final_state = simulate_forward(sub_search, i)
        val = evaluate_position(final_state)
        print(f"  Score: {val}")
        search_release(sub_search.searchId)

search_release(search_state.searchId)
