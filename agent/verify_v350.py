"""
v3.50 verification — extend Item 2's Clefairy-pivot gate to include Mist Energy.
    venv/bin/python agent/verify_v350.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import unittest
import policy
from policy import (
    _powerful_hand_walled, _blocker_gate_active, has_damage_blocker_revealed,
    handle_to_active,
    LILLIE_CLEFAIRY_EX, ALAKAZAM, TEAM_ROCKETS_ARTICUNO, MIST_ENERGY, PSYCHIC_ENERGY,
    OptionType, AreaType,
)
# reuse the proven mock helpers from the v3.49 suite
from verify_v349 import PokeMock, OptMock, _make_main_obs, _capture_scores


def _op_active_with_mist(nonblocker_id=65):
    return PokeMock(nonblocker_id, hp=200, energyCards=[PokeMock(MIST_ENERGY, hp=0)])


def _state(op_active, op_bench=None):
    class S:
        def __init__(s):
            s.players = [PokeMockState(), PokeMockState(op_active, op_bench)]
    class PokeMockState:
        def __init__(s, active=None, bench=None):
            s.active = [active] if active is not None else [None]
            s.bench = (bench or []) + [None] * (5 - len(bench or []))
    return S()


class V350_MistGate(unittest.TestCase):
    def test_walled_helper_true_on_mist_only(self):
        st = _state(_op_active_with_mist())              # Mist on active, no ability blocker
        self.assertTrue(_powerful_hand_walled(st, 1))

    def test_walled_helper_true_on_ability_blocker(self):
        st = _state(PokeMock(TEAM_ROCKETS_ARTICUNO, hp=120))
        self.assertTrue(_powerful_hand_walled(st, 1))

    def test_walled_helper_false_on_neither(self):
        st = _state(PokeMock(65, hp=100))
        self.assertFalse(_powerful_hand_walled(st, 1))

    def test_clefairy_attack_fires_vs_mist(self):
        clef = PokeMock(LILLIE_CLEFAIRY_EX, hp=200, energies=[PSYCHIC_ENERGY])
        obs = _make_main_obs(clef, [], [], _op_active_with_mist(), [])
        s = _capture_scores(obs, [OptMock(OptionType.ATTACK)])[0]
        self.assertGreaterEqual(s, 12000.0, "Clefairy attack must be prioritized vs Mist")

    def test_pivot_clefairy_up_vs_mist(self):
        obs = policy_to_active_obs()
        result = handle_to_active(obs, [OptMock(OptionType.YES, index=0),
                                        OptMock(OptionType.YES, index=1)], 1, 1)
        self.assertIn(0, result, "Vs Mist, Clefairy (idx 0) should be sent up over Alakazam")

    def test_rule_A_NOT_extended_to_mist(self):
        # Rule A stays ability-blocker-only: Mist alone must NOT trigger the blocker gate.
        from unittest.mock import MagicMock
        op = MagicMock(); op.active = [_op_active_with_mist()]; op.bench = [None] * 5
        self.assertFalse(_blocker_gate_active(op, PokeMock(ALAKAZAM, hp=140)),
                         "Mist alone must not trigger v3.48 Rule A (must stay untouched)")


def policy_to_active_obs():
    from unittest.mock import MagicMock
    obs = MagicMock(); obs.current.yourIndex = 0
    my = MagicMock(); op = MagicMock(); obs.current.players = [my, op]
    my.bench = [PokeMock(LILLIE_CLEFAIRY_EX, hp=200, energies=[PSYCHIC_ENERGY]),
                PokeMock(ALAKAZAM, hp=140, energies=[PSYCHIC_ENERGY]), None, None, None]
    op.active = [_op_active_with_mist()]; op.bench = [None] * 5
    return obs


if __name__ == "__main__":
    unittest.main(verbosity=2)
