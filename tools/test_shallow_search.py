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
    # Dummy evaluator for now: just hand size + 1000 if we won?
    # Actually, we need a real heuristic to prove it prefers Dawn over Attack.
    # Dawn increases hand size. Attack does damage.
    # We want to measure the state after the action.
    
    my_idx = search_state.observation.current.yourIndex
    my_state = search_state.observation.current.players[my_idx]
    opp_state = search_state.observation.current.players[1 - my_idx]
    
    # Hand size
    hand_size = len(my_state.hand) if my_state.hand else 0
    
    # Opponent active damage (actually HP left)
    opp_active = next((p for p in opp_state.active if p), None)
    opp_hp_left = opp_active.hp if opp_active else 0
    
    # Prize differential
    my_prizes = len([p for p in my_state.prize if p])
    opp_prizes = len([p for p in opp_state.prize if p])
    
    # Bench count
    bench_count = len([p for p in my_state.bench if p])
    
    score = 0.0
    score -= opp_prizes * 10000
    score += my_prizes * 10000
    score -= opp_hp_left * 10
    score += hand_size * 50
    score += bench_count * 20
    
    return score

# Dummy predictions for initialization
my_state = obs.current.players[obs.current.yourIndex]
opp_state = obs.current.players[1 - obs.current.yourIndex]

my_deck = [p.id for p in my_state.deck] if hasattr(my_state, 'deck') and my_state.deck else [1]*my_state.deckCount
my_prize = [1]*6
opp_deck = [1]*opp_state.deckCount
opp_prize = [1]*6
opp_hand = [1]*opp_state.handCount
opp_active = []
if opp_state.active and opp_state.active[0] is None:
    opp_active = [1] # dummy card ID

CARD_DB = {c.cardId: c for c in all_card_data()}
def get_card_name(cid):
    if not cid: return "None"
    return CARD_DB.get(cid).name if cid in CARD_DB else str(cid)

def simulate_forward(search_state, action_idx, max_chained=3):
    current_state = search_state
    
    # Step 1: Execute the chosen action
    current_state = search_step(current_state.searchId, [action_idx])
    
    # Step 2: Auto-resolve non-MAIN contexts (like picking cards for Dawn)
    chained = 1
    while current_state.observation.select and current_state.observation.select.context != SelectContext.MAIN:
        if chained >= max_chained or not current_state.observation.select.option:
            break
        # Just pick the first option
        current_state = search_step(current_state.searchId, [0])
        chained += 1
        
    # Step 3: If back to MAIN, check if we can ATTACK
    if current_state.observation.select and current_state.observation.select.context == SelectContext.MAIN:
        attack_idx = -1
        for i, opt in enumerate(current_state.observation.select.option):
            if opt.type == OptionType.ATTACK:
                attack_idx = i
                break
        if attack_idx >= 0:
            current_state = search_step(current_state.searchId, [attack_idx])
            
    return current_state

search_state = search_begin(obs, my_deck, my_prize, opp_deck, opp_prize, opp_hand, opp_active)

best_score = float('-inf')
best_opt = None

for i, opt in enumerate(search_state.observation.select.option):
    if opt.type in (OptionType.PLAY, OptionType.EVOLVE, OptionType.ATTACK):
        # Let's just test Dawn(idx=0), Evolve(idx=19), Attack(idx=21)
        if i not in [0, 19, 21]: continue
        
        cname = "Unknown"
        if opt.type == OptionType.PLAY and opt.index < len(my_state.hand):
            cname = get_card_name(my_state.hand[opt.index].id)
        elif opt.type == OptionType.EVOLVE:
            cname = "Evolve"
        elif opt.type == OptionType.ATTACK:
            cname = "Attack"
            
        print(f"\nSimulating {cname} (index {i})")
        
        # Clone state? search_begin doesn't let us clone the current search, we have to start a new search for each option!
        # Actually, if we just call search_begin for each option.
        sub_search = search_begin(obs, my_deck, my_prize, opp_deck, opp_prize, opp_hand, opp_active)
        final_state = simulate_forward(sub_search, i, max_chained=5)
        
        val = evaluate_position(final_state)
        print(f"  Score: {val}")
        search_release(sub_search.searchId)
        
search_release(search_state.searchId)
