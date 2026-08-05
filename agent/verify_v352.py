"""
v3.52 Item 1 verification — persist Clefairy attack (1a), no-retreat (1b),
windowed commit trigger (1c).
    venv/bin/python agent/verify_v352.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import unittest
import policy
from policy import (
    _update_clefairy_commitment, _clef_commit, WALL_COMMIT_WINDOW, WALL_COMMIT_THRESHOLD,
    LILLIE_CLEFAIRY_EX, PSYCHIC_ENERGY, MIST_ENERGY, OptionType, AreaType,
)
from verify_v349 import PokeMock, OptMock, _make_main_obs, _capture_scores
from verify_v351 import Pk, St, ala, blocker, plain, clef


# ── Item 1c — windowed commit trigger ────────────────────────────────────────
class Item1c_WindowedTrigger(unittest.TestCase):
    def setUp(self):
        _clef_commit.update(last_turn=None, window=[], committed=False)

    def _seq(self, walls):
        # feed a sequence of (walled?) our-turns; return committed after the last
        out = False
        for i, walled in enumerate(walls):
            op = blocker() if walled else plain()
            out = _update_clefairy_commitment(St(10 + 2 * i, ala(), op), 0, 1)
        return out

    def test_nonconsecutive_commits(self):
        # ep 90047497 shape: walled, gap, gap, walled -> 2 within a 4-window -> commit
        self.assertTrue(self._seq([True, False, False, True]))

    def test_flicker_commits(self):
        self.assertTrue(self._seq([True, False, True]))

    def test_single_walled_no_commit(self):
        self.assertFalse(self._seq([True, False, False]))

    def test_walled_outside_window_no_commit(self):
        # two walled turns 5 apart -> never 2 within any 4-window
        self.assertFalse(self._seq([True, False, False, False, True]))


# ── Item 1a — attack persists while committed ────────────────────────────────
class Item1a_AttackPersist(unittest.TestCase):
    def setUp(self):
        _clef_commit.update(last_turn=None, window=[], committed=False)

    def _attack_score(self, committed):
        obs = _make_main_obs(PokeMock(LILLIE_CLEFAIRY_EX, hp=200, energyCards=[PokeMock(PSYCHIC_ENERGY)] * 2),
                             [], [], PokeMock(65, hp=100), [])   # opp active plain -> wall OFF
        obs.current.turn = 12
        _clef_commit.update(last_turn=12, window=([True, True] if committed else []), committed=committed)
        return _capture_scores(obs, [OptMock(OptionType.ATTACK)])[0]

    def test_attack_high_when_committed_wall_off(self):
        self.assertGreaterEqual(self._attack_score(committed=True), 12000.0)

    def test_attack_low_when_not_committed_wall_off(self):
        self.assertLess(self._attack_score(committed=False), 12000.0)   # falls to 3000


# ── Item 1b — never abandon a powered active Clefairy ────────────────────────
class Item1b_NoRetreat(unittest.TestCase):
    def setUp(self):
        _clef_commit.update(last_turn=None, window=[], committed=False)

    def _retreat_score(self, committed, clef_e, status=False):
        clefm = PokeMock(LILLIE_CLEFAIRY_EX, hp=200, energyCards=[PokeMock(PSYCHIC_ENERGY)] * clef_e)
        obs = _make_main_obs(clefm, [], [], PokeMock(65, hp=100), [])
        obs.current.turn = 12
        if status:
            obs.current.players[0].confused = True
        _clef_commit.update(last_turn=12, window=([True, True] if committed else []), committed=committed)
        return _capture_scores(obs, [OptMock(OptionType.RETREAT)])[0]

    def test_powered_committed_clefairy_blocked(self):
        self.assertEqual(self._retreat_score(committed=True, clef_e=2), -9999.0)

    def test_status_cure_still_allows_retreat(self):
        self.assertNotEqual(self._retreat_score(committed=True, clef_e=2, status=True), -9999.0)

    def test_unpowered_clefairy_not_blocked(self):
        self.assertNotEqual(self._retreat_score(committed=True, clef_e=1), -9999.0)

    def test_uncommitted_unwalled_not_blocked(self):
        self.assertNotEqual(self._retreat_score(committed=False, clef_e=2), -9999.0)


def _run():
    groups = {
        "Item1c_WindowedTrigger": "Item 1c — windowed commit trigger",
        "Item1a_AttackPersist": "Item 1a — attack persists while committed",
        "Item1b_NoRetreat": "Item 1b — no-retreat of powered Clefairy",
    }
    loader = unittest.TestLoader(); ok = True
    print("=" * 66); print("  v3.52 verification"); print("=" * 66)
    for cls, label in groups.items():
        res = unittest.TextTestRunner(verbosity=0, stream=open(os.devnull, 'w')).run(
            loader.loadTestsFromTestCase(globals()[cls]))
        ok = ok and res.wasSuccessful()
        print(f"  [{'PASS' if res.wasSuccessful() else 'FAIL'}] {label}  ({res.testsRun} tests)")
        for k, cs in (("FAIL", res.failures), ("ERROR", res.errors)):
            for t, tb in cs: print(f"     {k}: {t}\n{tb}")
    print("=" * 66); print("  RESULT:", "ALL PASS" if ok else "FAILURES")
    return ok


if __name__ == "__main__":
    sys.exit(0 if _run() else 1)
