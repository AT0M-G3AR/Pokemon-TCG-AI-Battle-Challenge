"""
v3.51 Item 1 verification — persistent Clefairy-energize commitment.
    venv/bin/python agent/verify_v351.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import unittest
import policy
from policy import (
    _update_clefairy_commitment, _clef_commit, WALL_COMMIT_THRESHOLD,
    LILLIE_CLEFAIRY_EX, ALAKAZAM, TEAM_ROCKETS_ARTICUNO, MIST_ENERGY, PSYCHIC_ENERGY,
    OptionType, AreaType,
)
from verify_v349 import PokeMock, OptMock, _make_main_obs, _capture_scores


class Pk:
    def __init__(self, id, energyCards=None):
        self.id = id
        self.energyCards = energyCards or []

class Player:
    def __init__(self, active=None, bench=None):
        self.active = [active] if active is not None else [None]
        self.bench = (bench or []) + [None] * (5 - len(bench or []))

class St:
    def __init__(self, turn, my_active, op_active, my_bench=None):
        self.turn = turn
        self.players = [Player(my_active, my_bench), Player(op_active)]

def ala(): return Pk(ALAKAZAM)
def blocker(): return Pk(TEAM_ROCKETS_ARTICUNO)           # ability blocker -> walled
def plain(): return Pk(65)                                # not walled
def clef(e=0): return Pk(LILLIE_CLEFAIRY_EX, energyCards=[Pk(MIST_ENERGY)] * e)


class Item1_CommitLogic(unittest.TestCase):
    def setUp(self):
        _clef_commit.update(last_turn=None, window=[], committed=False)

    def test_two_walled_turns_commit(self):
        self.assertFalse(_update_clefairy_commitment(St(10, ala(), blocker()), 0, 1))  # streak 1
        self.assertTrue(_update_clefairy_commitment(St(12, ala(), blocker()), 0, 1))   # streak 2 -> commit

    def test_one_walled_turn_does_not_commit(self):
        self.assertFalse(_update_clefairy_commitment(St(10, ala(), blocker()), 0, 1))
        self.assertFalse(_clef_commit["committed"])

    def test_short_blip_resets(self):
        _update_clefairy_commitment(St(10, ala(), blocker()), 0, 1)   # streak 1
        _update_clefairy_commitment(St(12, ala(), plain()), 0, 1)     # not walled -> reset
        self.assertFalse(_clef_commit["committed"])

    def test_commit_holds_through_mist_flicker(self):
        _update_clefairy_commitment(St(10, ala(), blocker()), 0, 1)
        _update_clefairy_commitment(St(12, ala(), blocker()), 0, 1)   # committed
        # turn 14: wall momentarily False, but commit must HOLD (Clefairy not yet powered)
        self.assertTrue(_update_clefairy_commitment(St(14, ala(), plain(), my_bench=[clef(1)]), 0, 1))

    def test_commit_clears_when_clefairy_powered(self):
        _update_clefairy_commitment(St(10, ala(), blocker()), 0, 1)
        _update_clefairy_commitment(St(12, ala(), blocker()), 0, 1)
        # benched Clefairy now has 2 energy -> commitment done
        self.assertFalse(_update_clefairy_commitment(St(14, ala(), blocker(), my_bench=[clef(2)]), 0, 1))

    def test_resets_on_new_game(self):
        _update_clefairy_commitment(St(10, ala(), blocker()), 0, 1)
        _update_clefairy_commitment(St(12, ala(), blocker()), 0, 1)   # committed
        _update_clefairy_commitment(St(1, ala(), plain()), 0, 1)      # turn went backwards -> new game
        self.assertFalse(_clef_commit["committed"])
        # old walled history is gone — only the new game's first (unwalled) turn remains
        self.assertEqual(_clef_commit["window"], [False])


class Item1_EnergizeBehavior(unittest.TestCase):
    def setUp(self):
        _clef_commit.update(last_turn=None, window=[], committed=False)

    def _attach_score(self, committed, walled, clef_e):
        # Alakazam active; Clefairy benched with clef_e energy; energy in hand to attach to her.
        op_active = PokeMock(TEAM_ROCKETS_ARTICUNO, hp=120) if walled else PokeMock(65, hp=100)
        clefm = PokeMock(LILLIE_CLEFAIRY_EX, hp=200, energyCards=[PokeMock(MIST_ENERGY, hp=0)] * clef_e)
        obs = _make_main_obs(PokeMock(ALAKAZAM, hp=140), [clefm], [PokeMock(PSYCHIC_ENERGY, hp=0)],
                             op_active, [])
        obs.current.turn = 12
        if committed:
            _clef_commit.update(last_turn=12, window=[True, True], committed=True)
        else:
            _clef_commit.update(last_turn=12, window=[], committed=False)
        opt = OptMock(OptionType.ATTACH, index=0, inPlayArea=AreaType.BENCH, inPlayIndex=0)
        return _capture_scores(obs, [opt])[0]

    def test_committed_ramps_clefairy_from_one_energy(self):
        # committed, Clefairy already has 1 energy, wall momentarily off -> still attach 2nd (11000)
        self.assertGreaterEqual(self._attach_score(committed=True, walled=False, clef_e=1), 11000.0)

    def test_committed_energizes_from_zero(self):
        self.assertGreaterEqual(self._attach_score(committed=True, walled=False, clef_e=0), 11000.0)

    def test_walled_only_uses_base_score(self):
        s = self._attach_score(committed=False, walled=True, clef_e=0)
        self.assertGreaterEqual(s, 8000.0); self.assertLess(s, 11000.0)

    def test_no_wall_no_commit_no_priority(self):
        # not walled, not committed -> Clefairy energize should NOT get the high priority
        self.assertLess(self._attach_score(committed=False, walled=False, clef_e=0), 8000.0)


def _run():
    groups = {"Item1_CommitLogic": "Item 1 — commit/streak logic",
              "Item1_EnergizeBehavior": "Item 1 — energize behavior"}
    loader = unittest.TestLoader(); ok=True
    print("="*66); print("  v3.51 verification"); print("="*66)
    for cls,label in groups.items():
        res=unittest.TextTestRunner(verbosity=0, stream=open(os.devnull,'w')).run(loader.loadTestsFromTestCase(globals()[cls]))
        ok=ok and res.wasSuccessful()
        print(f"  [{'PASS' if res.wasSuccessful() else 'FAIL'}] {label}  ({res.testsRun} tests)")
        for k,cs in (("FAIL",res.failures),("ERROR",res.errors)):
            for t,tb in cs: print(f"     {k}: {t}\n{tb}")
    print("="*66); print("  RESULT:", "ALL PASS" if ok else "FAILURES")
    return ok

if __name__ == "__main__":
    sys.exit(0 if _run() else 1)
