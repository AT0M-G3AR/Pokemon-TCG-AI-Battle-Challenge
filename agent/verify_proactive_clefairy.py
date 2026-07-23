import sys, os
sys.path.insert(0, os.path.abspath('.'))

from policy import (
    has_articuno_revealed, _target_score, TEAM_ROCKETS_ARTICUNO
)

class MockCard:
    def __init__(self, cid):
        self.id = cid
        self.hp = 120 if cid == TEAM_ROCKETS_ARTICUNO else 60

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
    print("Testing has_articuno_revealed...")
    op_state = MockPlayer()
    
    # 1. Articuno not revealed
    assert not has_articuno_revealed(op_state), "Failed: Should be False"
    
    # 2. Articuno in discard
    op_state.discard.append(MockCard(TEAM_ROCKETS_ARTICUNO))
    assert not has_articuno_revealed(op_state), "Failed: Should ignore discard"
    
    # 3. Articuno on bench
    op_state.bench.append(MockCard(TEAM_ROCKETS_ARTICUNO))
    assert has_articuno_revealed(op_state), "Failed: Should be True"
    print("  -> Passed!")

    print("\nTesting Target Scoring...")
    score_normal = _target_score(MockCard(1), 6, 0)
    score_articuno = _target_score(MockCard(TEAM_ROCKETS_ARTICUNO), 6, 0)
    print(f"Normal 60HP: {score_normal}, Articuno 120HP: {score_articuno}")
    assert score_articuno > score_normal + 4000, "Articuno should have huge bonus"
    print("  -> Passed!")

if __name__ == '__main__':
    run_tests()
    print("All forced-state tests passed.")
