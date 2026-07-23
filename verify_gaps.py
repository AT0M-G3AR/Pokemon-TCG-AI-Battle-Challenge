class AreaType:
    ACTIVE = 4
    BENCH = 5

LILLIE_CLEFAIRY_EX = 272
ALAKAZAM = 743
PSYCHIC_ENERGY = 19
DUNSPARCE = 65
DUDUNSPARCE = 66


def print_attach_scores(energy_id, targets):
    print(f"Energy: {energy_id}")
    for target in targets:
        tid = target['id']
        area = target['area']
        energy_count = target['energy']
        score = 0.0
        
        if energy_id == PSYCHIC_ENERGY:
            if tid == DUNSPARCE or tid == DUDUNSPARCE:
                score = -9999.0
            elif tid == ALAKAZAM:
                if energy_count >= 1:
                    score = 5000.0
                else:
                    score = 9000.0
            elif tid == LILLIE_CLEFAIRY_EX:
                if area == AreaType.ACTIVE and energy_count < 2:
                    score = 6000.0
                else:
                    score = -9999.0
            else:
                score = -9999.0
        
        print(f"  Target: {tid}, Area: {area}, Energy: {energy_count} -> Score: {score}")

def print_search_scores(field_dunsparce_count):
    print(f"Field Dunsparce count: {field_dunsparce_count}")
    for cid in [DUNSPARCE, DUDUNSPARCE]:
        score = 0.0
        if cid == DUDUNSPARCE:
            if field_dunsparce_count >= 1:
                score = 9500.0
            else:
                score = 4000.0
        elif cid == DUNSPARCE:
            if field_dunsparce_count == 0:
                score = 9600.0
            elif field_dunsparce_count < 3:
                score = 5000.0
            else:
                score = 500.0
        print(f"  Option: {cid} -> Score: {score}")

if __name__ == '__main__':
    print("=== Verification: Clefairy Energy Gap ===")
    targets = [
        {'id': LILLIE_CLEFAIRY_EX, 'area': AreaType.ACTIVE, 'energy': 0},
        {'id': LILLIE_CLEFAIRY_EX, 'area': AreaType.BENCH, 'energy': 0},
        {'id': ALAKAZAM, 'area': AreaType.BENCH, 'energy': 1},
        {'id': ALAKAZAM, 'area': AreaType.BENCH, 'energy': 0},
    ]
    print_attach_scores(PSYCHIC_ENERGY, targets)
    
    print("\n=== Verification: Poké Pad Dudunsparce Trap ===")
    print_search_scores(0)
    print_search_scores(1)
