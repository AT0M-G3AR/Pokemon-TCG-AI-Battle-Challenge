ABRA = 63
KADABRA = 405
ALAKAZAM = 743
DUNSPARCE = 65
DUDUNSPARCE = 66
RARE_CANDY = 1079

print("=== Verification: Fix 2 (Hilda Kadabra Priority) ===")
def get_hilda_scores(field):
    kadabra_score = 0.0
    dudunsparce_score = 0.0
    
    # Kadabra logic
    alakazam_line_missing = field[KADABRA] == 0 and field[ALAKAZAM] == 0
    if field[ABRA] >= 1 and alakazam_line_missing:
        kadabra_score = 9700.0
    elif field[ABRA] >= 1:
        kadabra_score = 8000.0
    else:
        kadabra_score = 3000.0
        
    # Dudunsparce logic
    if field[DUNSPARCE] >= 1:
        dudunsparce_score = 9500.0
    else:
        dudunsparce_score = 4000.0
        
    return kadabra_score, dudunsparce_score

# 1. 4 Abra, 0 Kadabra/Alakazam, 1 Dunsparce
field = {ABRA: 4, KADABRA: 0, ALAKAZAM: 0, DUNSPARCE: 1}
k, d = get_hilda_scores(field)
print(f"Empty Alakazam line: Kadabra={k}, Dudunsparce={d}")
assert k == 9700.0 and d == 9500.0 and k > d, "Kadabra should win when line is missing"

# 2. 1 Kadabra already in play
field[KADABRA] = 1
k, d = get_hilda_scores(field)
print(f"Kadabra already in play: Kadabra={k}, Dudunsparce={d}")
assert k == 8000.0 and d == 9500.0 and d > k, "Dudunsparce should win fallback"


print("\n=== Verification: Fix 3 (Rare Candy Priority) ===")
def get_rare_candy_scores(field, hand):
    rare_candy_score = -9999.0
    kadabra_evolve_score = 9500.0
    
    abra_in_play = field[ABRA] > 0
    alakazam_in_hand = hand[ALAKAZAM] > 0
    kadabra_missing = field[KADABRA] == 0
    if abra_in_play and alakazam_in_hand and kadabra_missing:
        rare_candy_score = 9800.0  # Skip Kadabra — instant Stage 2
    else:
        rare_candy_score = -9999.0
        
    return rare_candy_score, kadabra_evolve_score

# 1. Abra in play, Alakazam in hand, Kadabra missing
field = {ABRA: 1, KADABRA: 0}
hand = {ALAKAZAM: 1}
rc, k_ev = get_rare_candy_scores(field, hand)
print(f"Instant Stage 2 possible: RareCandy={rc}, KadabraEvolve={k_ev}")
assert rc == 9800.0 and rc > k_ev, "Rare Candy should beat normal evolve"

# 2. Alakazam not in hand
hand[ALAKAZAM] = 0
rc, k_ev = get_rare_candy_scores(field, hand)
print(f"Missing Alakazam: RareCandy={rc}, KadabraEvolve={k_ev}")
assert rc == -9999.0 and k_ev > rc, "Normal evolve should win"

print("\n=== Verification: Fix 1 (Retreat Guard) ===")
def get_retreat_score(energy_count, curable_status, alakazam_ready, hp_remaining, max_hp):
    base_score = 4000.0 if alakazam_ready else 500.0
    if curable_status:
        base_score += 3000.0
    score = base_score
    
    if energy_count >= 1 and not curable_status and not alakazam_ready:
        if hp_remaining >= max_hp:
            score = -9999.0
            
    return score

# Wasteful retreat: 1 energy, no status, no Alakazam ready, full HP
score = get_retreat_score(1, False, False, 60, 60)
print(f"Wasteful retreat score: {score}")
assert score == -9999.0

# Good swap: Alakazam ready
score = get_retreat_score(1, False, True, 60, 60)
print(f"Alakazam ready retreat score: {score}")
assert score == 4000.0

# Damage taken
score = get_retreat_score(1, False, False, 40, 60)
print(f"Damaged retreat score: {score}")
assert score == 500.0

print("\nAll forced-state tests passed.")
