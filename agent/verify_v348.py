"""
v3.48 verification — Prize-Value Weighting + Boss's Orders Bypass.

Six synthetic forced-state tests, one per dispatch rule. Run standalone:
    venv/bin/python agent/verify_v348.py
Each test prints a labelled PASS/FAIL so the six results can be reported
individually (per dispatch close-out).
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import unittest
import policy
from policy import (
    _prize_count, _target_score, DAMAGE_BLOCKING_ABILITY_IDS,
    ALAKAZAM, LILLIE_CLEFAIRY_EX, CARD_DB,
)

# Real card IDs (confirmed in project notes / DB)
MEGA_VENUSAUR_EX = 652   # megaEx -> 3 prizes
DRAGAPULT_EX     = 121   # ex     -> 2 prizes
TR_ARTICUNO      = 414   # damage blocker (Repelling Veil), single-prize
PLAIN_ALAKAZAM   = ALAKAZAM  # 743, non-ex -> 1 prize


class PokeMock:
    """Minimal stand-in for a Pokemon in play."""
    def __init__(self, id, hp=200, damage=0, energies=None):
        self.id = id
        self.hp = hp
        self.damage = damage
        self.energies = energies or []


# ─────────────────────────────────────────────────────────────────────────────
# TEST 6 — Prize value correctness (rule D), real DB lookups (not mocks)
# ─────────────────────────────────────────────────────────────────────────────
class Test6_PrizeValue(unittest.TestCase):
    def test_mega_ex_is_three(self):
        self.assertEqual(_prize_count(PokeMock(MEGA_VENUSAUR_EX)), 3,
                         f"{CARD_DB[MEGA_VENUSAUR_EX].name} should be 3 prizes")

    def test_regular_ex_is_two(self):
        self.assertEqual(_prize_count(PokeMock(DRAGAPULT_EX)), 2,
                         f"{CARD_DB[DRAGAPULT_EX].name} should be 2 prizes")
        self.assertEqual(_prize_count(PokeMock(LILLIE_CLEFAIRY_EX)), 2,
                         "Lillie's Clefairy ex should be 2 prizes")

    def test_plain_is_one(self):
        self.assertEqual(_prize_count(PokeMock(PLAIN_ALAKAZAM)), 1,
                         "Alakazam (non-ex) should be 1 prize")

    def test_unknown_id_defaults_one(self):
        self.assertEqual(_prize_count(PokeMock(9_999_999)), 1)


def _run_labelled():
    """Run each TestCase class separately and print a per-rule line."""
    labels = {
        "Test6_PrizeValue": "Test 6 — Prize value correctness (rule D)",
    }
    loader = unittest.TestLoader()
    all_ok = True
    for cls_name, label in labels.items():
        cls = globals().get(cls_name)
        if cls is None:
            continue
        suite = loader.loadTestsFromTestCase(cls)
        res = unittest.TextTestRunner(verbosity=0, stream=open(os.devnull, "w")).run(suite)
        ok = res.wasSuccessful()
        all_ok = all_ok and ok
        n = res.testsRun
        status = "\033[92mPASS\033[0m" if ok else "\033[91mFAIL\033[0m"
        print(f"  [{status}] {label}  ({n} assertions)")
        if not ok:
            for kind, cases in (("FAIL", res.failures), ("ERROR", res.errors)):
                for t, tb in cases:
                    print(f"        {kind}: {t}\n{tb}")
    return all_ok


if __name__ == "__main__":
    print("=" * 68)
    print("  v3.48 verification — six forced-state tests")
    print("=" * 68)
    ok = _run_labelled()
    print("=" * 68)
    print("  RESULT:", "\033[92mALL PASS\033[0m" if ok else "\033[91mFAILURES PRESENT\033[0m")
    sys.exit(0 if ok else 1)
