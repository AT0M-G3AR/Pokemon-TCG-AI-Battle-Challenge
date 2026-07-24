import sys, os
sys.path.insert(0, os.path.abspath('.'))

from policy import (
    has_damage_blocker_revealed, _target_score, DAMAGE_BLOCKING_ABILITY_IDS
)

class MockCard:
    def __init__(self, cid):
        self.id = cid
        self.hp = 120 if cid in DAMAGE_BLOCKING_ABILITY_IDS else 60

class MockPlayer:
    def __init__(self):
        self.active = []
        self.bench = []
        self.discard = []

import policy
policy._energy_count = lambda x: 0
policy._hp_remaining = lambda x: getattr(x, 'hp', 60)
policy._prize_count = lambda x: 1

def run_tests():
    print("Testing has_damage_blocker_revealed...")
    op_state = MockPlayer()
    
    # 1. No blockers revealed
    assert not has_damage_blocker_revealed(op_state), "Failed: Should be False"
    
    # 2. Non-blocker on bench
    op_state.bench.append(MockCard(1))
    assert not has_damage_blocker_revealed(op_state), "Failed: Should be False with normal card"
    
    # 3. Rabsca in discard (should ignore)
    op_state.discard.append(MockCard(74))
    assert not has_damage_blocker_revealed(op_state), "Failed: Should ignore discard"
    
    # 4. Rabsca on bench
    op_state.bench.append(MockCard(74))
    assert has_damage_blocker_revealed(op_state), "Failed: Should be True for Rabsca"
    print("  -> Passed!")

    print("\nTesting Target Scoring...")
    score_normal = _target_score(MockCard(1), 6, 0)
    score_rabsca = _target_score(MockCard(74), 6, 0)
    score_articuno = _target_score(MockCard(414), 6, 0)
    
    print(f"Normal 60HP: {score_normal}")
    print(f"Rabsca (Blocker) 120HP: {score_rabsca}")
    print(f"Articuno (Blocker) 120HP: {score_articuno}")
    
    assert score_rabsca > score_normal + 4000, "Rabsca should have massive blocker bonus"
    assert score_articuno > score_normal + 4000, "Articuno should have massive blocker bonus"
    assert score_rabsca == score_articuno, "All blockers should have equal base threat scoring"
    print("  -> Passed!")

if __name__ == '__main__':
    run_tests()
    print("All forced-state tests passed.")
