import sys
import os

# Add agent dir to path so we can import search_api
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../agent')))
from search_api import evaluate_attack

class MockEnergy:
    def __init__(self, id):
        self.id = id

class MockPokemon:
    def __init__(self, hp, energies=None):
        self.hp = hp
        self.energyCards = energies or []

class MockPlayerState:
    def __init__(self, active_pokemon):
        self.active = [active_pokemon]

class MockCurrentState:
    def __init__(self, op_state):
        self.yourIndex = 0
        self.players = [None, op_state]

class MockObservation:
    def __init__(self, op_state):
        self.current = MockCurrentState(op_state)

def test_evaluate_attack():
    print("Running evaluate_attack edge cases...")
    
    # CASE A: op_bench_count == 0 and lethal -> should return 50000.0
    # Opponent has 60 HP, we have 4 cards (4*20 = 80 damage).
    obs_a = MockObservation(MockPlayerState(MockPokemon(60)))
    score_a = evaluate_attack(obs_a, attack_index=1, opponent_hp=60, hand_size=4, my_prizes_left=6, opponent_prizes_left=6, op_bench_count=0)
    print(f"CASE A (Empty Bench, Lethal): Score = {score_a}")
    assert score_a == 50000.0, f"Expected 50000.0, got {score_a}"

    # CASE B: op_bench_count > 0 and lethal -> should return 20000.0 (Tier 1)
    obs_b = MockObservation(MockPlayerState(MockPokemon(60)))
    score_b = evaluate_attack(obs_b, attack_index=1, opponent_hp=60, hand_size=4, my_prizes_left=6, opponent_prizes_left=6, op_bench_count=1)
    print(f"CASE B (Bench > 0, Lethal): Score = {score_b}")
    assert score_b == 20000.0, f"Expected 20000.0, got {score_b}"

    # CASE C: op_bench_count == 0, Mist Energy present (ID 11) -> should NOT return 50000.0 (should return 3000.0 since 0 damage)
    obs_c = MockObservation(MockPlayerState(MockPokemon(60, [MockEnergy(11)])))
    score_c = evaluate_attack(obs_c, attack_index=1, opponent_hp=60, hand_size=4, my_prizes_left=6, opponent_prizes_left=6, op_bench_count=0)
    print(f"CASE C (Empty Bench, Mist Energy): Score = {score_c}")
    assert score_c == 3000.0, f"Expected 3000.0, got {score_c}"

    print("All tests PASSED.")

if __name__ == '__main__':
    test_evaluate_attack()
