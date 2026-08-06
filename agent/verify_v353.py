"""
v3.53 Item 1 fix verification — latch-until-attacked.

The bug (live, ep 90286383): the wall-commitment cleared the moment a benched Clefairy
reached 2 energy, so if a transient wall (esp. Mist) dropped in the gap between powering
and pivoting, Item 1a's gate read False by the time she was active and Full Moon Rondo
never fired (she sat active e2 with the attack offered T20-24 and passed every turn).

Fix: hold the latch through the pivot AND the swing — release it only once Clefairy has
ACTUALLY thrown Full Moon Rondo (cleared at the end of handle_main when her attack option
is the selected move).
    venv/bin/python agent/verify_v353.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import unittest
from unittest.mock import patch
import policy
from policy import (
    _update_clefairy_commitment, _clef_commit,
    LILLIE_CLEFAIRY_EX, ALAKAZAM, PSYCHIC_ENERGY, OptionType,
)
from verify_v349 import PokeMock, OptMock, _make_main_obs
from verify_v351 import St, ala, blocker, plain, clef


def _run_main(obs, options, mn=1, mx=1):
    """Run the REAL handle_main (real _pick_best, so the latch-clear path executes);
    only _sanity_check is stubbed to a pass-through to keep the mock obs simple."""
    with patch.object(policy, '_sanity_check', side_effect=lambda o, ops, sc: sc):
        return policy.handle_main(obs, options, mn, mx)


# ── Latch is NOT released merely by reaching 2 energy (the core regression) ──────
class LatchHoldsAfterPowered(unittest.TestCase):
    def setUp(self):
        _clef_commit.update(last_turn=None, window=[], committed=False)

    def test_not_cleared_at_2_energy_while_still_walled(self):
        _update_clefairy_commitment(St(10, ala(), blocker()), 0, 1)
        _update_clefairy_commitment(St(12, ala(), blocker()), 0, 1)   # committed
        # benched Clefairy now has 2 energy — OLD behavior cleared here; must now HOLD
        self.assertTrue(_update_clefairy_commitment(St(14, ala(), blocker(), my_bench=[clef(2)]), 0, 1))
        self.assertTrue(_clef_commit["committed"])

    def test_holds_when_wall_drops_after_powering(self):
        # exact ep 90286383 shape: walled -> powered on bench -> wall DROPS while she's
        # still benched e2. Latch must survive the drop so she can pivot up and swing.
        _update_clefairy_commitment(St(10, ala(), blocker()), 0, 1)
        _update_clefairy_commitment(St(12, ala(), blocker()), 0, 1)   # committed
        _update_clefairy_commitment(St(14, ala(), blocker(), my_bench=[clef(2)]), 0, 1)  # powered
        # turns 16/18: wall gone (plain), Clefairy powered on bench, not yet attacked
        self.assertTrue(_update_clefairy_commitment(St(16, ala(), plain(), my_bench=[clef(2)]), 0, 1))
        self.assertTrue(_update_clefairy_commitment(St(18, ala(), plain(), my_bench=[clef(2)]), 0, 1))


# ── THE missing case — powered active Clefairy fires though the wall has dropped ─
class PoweredClefairyFiresAndLatchClears(unittest.TestCase):
    def setUp(self):
        _clef_commit.update(last_turn=None, window=[], committed=False)

    def _obs_active_clef(self, clef_e=2, turn=20):
        obs = _make_main_obs(
            PokeMock(LILLIE_CLEFAIRY_EX, hp=200, energyCards=[PokeMock(PSYCHIC_ENERGY)] * clef_e),
            [], [], PokeMock(65, hp=100), [])   # opp active plain -> wall OFF
        obs.current.turn = turn
        return obs

    def test_powered_active_clefairy_fires_when_wall_dropped(self):
        # committed earlier (walled then dropped); she's now active e2, wall OFF.
        _clef_commit.update(last_turn=18, window=[True, False, False], committed=True)
        obs = self._obs_active_clef()
        result = _run_main(obs, [OptMock(OptionType.ATTACK), OptMock(OptionType.END)])
        # Full Moon Rondo (index 0) is chosen over END — she FIRES (was 0/… live)
        self.assertEqual(result, [0])
        # …and only NOW is the latch released (the swing is done)
        self.assertFalse(_clef_commit["committed"])

    def test_latch_not_released_when_attack_not_taken(self):
        # committed, powered active Clefairy, but no ATTACK offered this decision point
        # (e.g. a mid-turn sub-decision). Latch must persist until she actually swings.
        _clef_commit.update(last_turn=18, window=[True, False, False], committed=True)
        obs = self._obs_active_clef()
        result = _run_main(obs, [OptMock(OptionType.END)])
        self.assertTrue(_clef_commit["committed"])


def _run():
    groups = {
        "LatchHoldsAfterPowered": "Latch holds after powering (no premature clear)",
        "PoweredClefairyFiresAndLatchClears": "Powered active Clefairy fires; latch clears on swing",
    }
    loader = unittest.TestLoader(); ok = True
    print("=" * 66); print("  v3.53 verification — latch-until-attacked"); print("=" * 66)
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
