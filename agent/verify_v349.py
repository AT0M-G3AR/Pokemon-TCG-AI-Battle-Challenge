"""
v3.49 verification — Targeting Intelligence.
Forced-state tests, grouped by dispatch item. Run standalone:
    venv/bin/python agent/verify_v349.py
Each group prints a labelled PASS/FAIL so results can be reported individually.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import unittest
import policy
from policy import (
    _target_score, _munkidori_in_play, _cage_relevant_threat,
    COUNTER_MOVING_ABILITY_IDS, COUNTER_MOVER_DRAG_BONUS, CAGE_BLOCKED_THREAT_IDS,
    MUNKIDORI, FROSLASS, DREEPY, DRAKLOAK, DRAGAPULT_EX,
)

# Real IDs used as forced-state targets
MEGA_EX = 652        # Mega Venusaur ex -> 3 prizes
REG_EX  = DRAGAPULT_EX  # 121 -> 2 prizes
PLAIN   = 65         # Dunsparce -> 1 prize


class PokeMock:
    def __init__(self, id, hp=120, damage=0, energies=None):
        self.id = id; self.hp = hp; self.damage = damage
        self.energies = energies or []

class OpStateMock:
    def __init__(self, active=None, bench=None):
        self.active = active or [None]
        self.bench = bench or [None] * 5


# ── ITEM 1a — Munkidori Boss's Orders drag priority ──────────────────────────
class Item1a_MunkidoriDragPriority(unittest.TestCase):
    def test_killable_munkidori_is_top_drag_target(self):
        dmg = 200
        munk  = _target_score(PokeMock(MUNKIDORI, hp=110), 6, current_damage=dmg)
        mega  = _target_score(PokeMock(MEGA_EX,  hp=200), 6, current_damage=dmg)
        reg   = _target_score(PokeMock(REG_EX,   hp=120), 6, current_damage=dmg)
        plain = _target_score(PokeMock(PLAIN,    hp=60),  6, current_damage=dmg)
        self.assertGreater(munk, mega,  "Munkidori should outrank a killable 3-prize Mega ex")
        self.assertGreater(munk, reg,   "Munkidori should outrank a killable 2-prize ex")
        self.assertGreater(munk, plain, "Munkidori should outrank a killable generic")

    def test_bonus_gated_on_killable(self):
        # current_damage below Munkidori's HP -> not killable -> NO drag bonus
        no_ko = _target_score(PokeMock(MUNKIDORI, hp=110), 6, current_damage=100)
        ko    = _target_score(PokeMock(MUNKIDORI, hp=110), 6, current_damage=200)
        self.assertLess(no_ko, 1000.0, "Un-killable Munkidori must not receive the drag bonus")
        self.assertGreaterEqual(ko - no_ko, COUNTER_MOVER_DRAG_BONUS,
                                "Killable Munkidori must include the drag bonus")

    def test_non_countermover_scoring_unchanged(self):
        # A killable 2-prize ex keeps its exact v3.48 score (no counter bonus leaks in)
        s = _target_score(PokeMock(REG_EX, hp=120), 6, current_damage=200)
        expected = 10000.0 + 2 * 3000.0 - 120 * 0.3   # killable + prize(2) + hp tiebreak
        self.assertAlmostEqual(s, expected, places=6)

    def test_blocker_gate_still_suppresses_munkidori(self):
        # Rule A untouched: under the blocker gate a non-blocker (Munkidori) is suppressed
        s = _target_score(PokeMock(MUNKIDORI, hp=110), 6, current_damage=200, blocker_gate=True)
        self.assertLess(s, 0.0, "Blocker gate must still suppress non-blockers (Rule A intact)")

    def test_munkidori_in_play_routes_through_set(self):
        op = OpStateMock(bench=[PokeMock(MUNKIDORI, hp=110), None, None, None, None])
        self.assertTrue(_munkidori_in_play(op))
        self.assertIn(MUNKIDORI, COUNTER_MOVING_ABILITY_IDS)
        self.assertNotIn(139, COUNTER_MOVING_ABILITY_IDS)  # Munkidori ex excluded
        self.assertFalse(_munkidori_in_play(OpStateMock(bench=[PokeMock(PLAIN, hp=60)])))


# ── ITEM 1b — Battle Cage trigger generalization ─────────────────────────────
class Item1b_CageTrigger(unittest.TestCase):
    def test_froslass_now_triggers_cage(self):
        op = OpStateMock(active=[PokeMock(PLAIN, hp=60)],
                         bench=[PokeMock(FROSLASS, hp=90), None, None, None, None])
        self.assertTrue(_cage_relevant_threat(op), "Froslass Freezing Shroud must trigger Cage")
        self.assertIn(FROSLASS, CAGE_BLOCKED_THREAT_IDS)

    def test_munkidori_triggers_cage(self):
        op = OpStateMock(bench=[PokeMock(MUNKIDORI, hp=110)])
        self.assertTrue(_cage_relevant_threat(op))

    def test_dragapult_line_still_triggers_cage(self):
        # regression: former Dragapult-only trigger preserved
        for cid in (DREEPY, DRAKLOAK, DRAGAPULT_EX):
            self.assertTrue(_cage_relevant_threat(OpStateMock(active=[PokeMock(cid, hp=120)])),
                            f"id {cid} should still trigger Cage")

    def test_irrelevant_board_does_not_trigger(self):
        op = OpStateMock(active=[PokeMock(PLAIN, hp=60)], bench=[PokeMock(MEGA_EX, hp=300)])
        self.assertFalse(_cage_relevant_threat(op), "No bench-counter threat -> no Cage boost")


def _run():
    groups = {
        "Item1a_MunkidoriDragPriority": "Item 1a — Munkidori Boss's Orders drag priority",
        "Item1b_CageTrigger": "Item 1b — Battle Cage trigger generalization",
    }
    loader = unittest.TestLoader(); ok_all = True
    print("=" * 70); print("  v3.49 verification"); print("=" * 70)
    for cls_name, label in groups.items():
        suite = loader.loadTestsFromTestCase(globals()[cls_name])
        res = unittest.TextTestRunner(verbosity=0, stream=open(os.devnull, "w")).run(suite)
        ok = res.wasSuccessful(); ok_all = ok_all and ok
        print(f"  [{'PASS' if ok else 'FAIL'}] {label}  ({res.testsRun} tests)")
        for kind, cases in (("FAIL", res.failures), ("ERROR", res.errors)):
            for t, tb in cases:
                print(f"      {kind}: {t}\n{tb}")
    print("=" * 70); print("  RESULT:", "ALL PASS" if ok_all else "FAILURES")
    return ok_all


if __name__ == "__main__":
    sys.exit(0 if _run() else 1)
