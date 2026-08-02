"""
v3.49 verification — Targeting Intelligence.
Forced-state tests, grouped by dispatch item. Run standalone:
    venv/bin/python agent/verify_v349.py
Each group prints a labelled PASS/FAIL so results can be reported individually.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import unittest
from unittest.mock import MagicMock, patch
import policy
from policy import (
    _target_score, _munkidori_in_play, _cage_relevant_threat, _blocker_gate_active,
    _boss_drag_decision, handle_to_active, handle_main,
    COUNTER_MOVING_ABILITY_IDS, COUNTER_MOVER_DRAG_BONUS, CAGE_BLOCKED_THREAT_IDS,
    MUNKIDORI, FROSLASS, DREEPY, DRAKLOAK, DRAGAPULT_EX,
    LILLIE_CLEFAIRY_EX, ALAKAZAM, TEAM_ROCKETS_ARTICUNO, PSYCHIC_ENERGY,
    OptionType, AreaType,
)

# Real IDs used as forced-state targets
MEGA_EX = 652        # Mega Venusaur ex -> 3 prizes
REG_EX  = DRAGAPULT_EX  # 121 -> 2 prizes
PLAIN   = 65         # Dunsparce -> 1 prize


class PokeMock:
    def __init__(self, id, hp=120, damage=0, energies=None, energyCards=None):
        self.id = id; self.hp = hp; self.damage = damage
        self.energies = energies or []
        self.energyCards = energyCards or []

class OpStateMock:
    def __init__(self, active=None, bench=None):
        self.active = active or [None]
        self.bench = bench or [None] * 5

class OptMock:
    def __init__(self, type, index=0, inPlayArea=None, inPlayIndex=0):
        self.type = type; self.index = index
        self.inPlayArea = inPlayArea; self.inPlayIndex = inPlayIndex


def _make_main_obs(my_active, my_bench, my_hand, op_active, op_bench):
    """MagicMock obs for handle_main, mirroring verify_energy_blocks' proven setup."""
    obs = MagicMock()
    obs.current.yourIndex = 0
    my = MagicMock(); op = MagicMock()
    obs.current.players = [my, op]
    obs.current.supporterPlayed = False
    obs.current.energyAttached = False
    obs.current.stadium = []
    my.deckCount = 40; my.prize = [1, 2, 3, 4, 5, 6]
    my.hand = my_hand; my.bench = my_bench + [None] * (5 - len(my_bench))
    my.active = [my_active]; my.discard = []
    my.asleep = my.paralyzed = my.confused = my.poisoned = my.burned = False
    op.prize = [1, 2, 3, 4, 5, 6]
    op.active = [op_active]; op.bench = op_bench + [None] * (5 - len(op_bench)); op.discard = []
    return obs


def _capture_scores(obs, options):
    out = {}
    with patch.object(policy, '_sanity_check', side_effect=lambda o, ops, sc: out.__setitem__('s', list(sc))):
        with patch.object(policy, '_pick_best', return_value=[0]):
            handle_main(obs, options, 1, 1)
    return out.get('s', [])


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


# ── ITEM 2 — Clefairy pivot-when-walled ──────────────────────────────────────
class Item2_ClefairyPivot(unittest.TestCase):
    def test_clefairy_attack_prioritized_when_walled(self):
        # Clefairy active, opponent has Repelling Veil blocker -> Full Moon Rondo
        # scores high (bypass), vs a control with no blocker.
        clef = PokeMock(LILLIE_CLEFAIRY_EX, hp=200, energies=[PSYCHIC_ENERGY])
        atk = OptMock(OptionType.ATTACK)
        walled = _make_main_obs(clef, [], [], PokeMock(TEAM_ROCKETS_ARTICUNO, hp=120), [])
        clear  = _make_main_obs(PokeMock(LILLIE_CLEFAIRY_EX, hp=200, energies=[PSYCHIC_ENERGY]),
                                [], [], PokeMock(65, hp=100), [])
        s_walled = _capture_scores(walled, [atk])[0]
        s_clear  = _capture_scores(clear, [OptMock(OptionType.ATTACK)])[0]
        self.assertGreaterEqual(s_walled, 12000.0, "Walled Clefairy attack must be high-priority")
        self.assertGreater(s_walled, s_clear, "Blocker present should raise the Clefairy attack score")

    def test_energy_to_clefairy_prioritized_when_walled(self):
        clef = PokeMock(LILLIE_CLEFAIRY_EX, hp=200, energyCards=[])
        energy = PokeMock(PSYCHIC_ENERGY, hp=0)
        obs = _make_main_obs(clef, [], [energy], PokeMock(TEAM_ROCKETS_ARTICUNO, hp=120), [])
        opt = OptMock(OptionType.ATTACH, index=0, inPlayArea=AreaType.ACTIVE, inPlayIndex=0)
        s = _capture_scores(obs, [opt])[0]
        self.assertGreaterEqual(s, 8000.0, "Energy should be routed to Clefairy when walled")

    def test_pivot_clefairy_up_when_walled(self):
        # handle_to_active: bench has Clefairy + Alakazam, opp has a blocker.
        obs = MagicMock(); obs.current.yourIndex = 0
        my = MagicMock(); op = MagicMock(); obs.current.players = [my, op]
        my.bench = [PokeMock(LILLIE_CLEFAIRY_EX, hp=200, energies=[PSYCHIC_ENERGY]),
                    PokeMock(ALAKAZAM, hp=140, energies=[PSYCHIC_ENERGY]), None, None, None]
        op.active = [PokeMock(TEAM_ROCKETS_ARTICUNO, hp=120)]; op.bench = [None] * 5
        opts = [OptMock(OptionType.YES, index=0), OptMock(OptionType.YES, index=1)]
        result = handle_to_active(obs, opts, 1, 1)
        self.assertIn(0, result, "Walled: Clefairy (index 0) should be sent up over Alakazam")

    def test_rule_A_still_suppresses(self):
        # Regression: v3.48 Rule A untouched — gate active for Alakazam+blocker,
        # and a non-blocker is still suppressed under blocker_gate.
        op = OpStateMock(active=[PokeMock(TEAM_ROCKETS_ARTICUNO, hp=120)])
        self.assertTrue(_blocker_gate_active(op, PokeMock(ALAKAZAM, hp=140)))
        self.assertLess(_target_score(PokeMock(65, hp=60), 6, current_damage=200, blocker_gate=True), 0.0)


# ── ITEM 3 — Boss's Orders hand-sufficiency check ────────────────────────────
class Item3_BossHandSufficiency(unittest.TestCase):
    FROS = FROSLASS          # 90 HP bench threat, the wrongly-dragged target
    BUDEW = 999              # stand-in for the killable bench basic (Budew) that was left untouched
    TANK  = 648              # opponent active tank (Grimmsnarl ex, 320) — not killable

    def test_decline_when_target_not_killable_postdraw(self):
        # Bigoldgaryman: post-draw hand only reaches ~60 dmg; Froslass (90) can't be
        # KO'd -> the corrected logic must NOT spend Boss dragging it.
        op_bench = [PokeMock(self.FROS, hp=90)]
        op_active = PokeMock(self.TANK, hp=320)
        _, should = _boss_drag_decision(op_bench, op_active, 6, current_dmg=60)
        self.assertFalse(should, "Must not Boss a target we can't KO with the post-draw hand")

    def test_prefers_killable_alternative_over_froslass(self):
        # Same board but the killable Budew is on the bench: pick it, not Froslass.
        op_bench = [PokeMock(self.FROS, hp=90), PokeMock(self.BUDEW, hp=40)]
        op_active = PokeMock(self.TANK, hp=320)
        target, should = _boss_drag_decision(op_bench, op_active, 6, current_dmg=60)
        self.assertTrue(should, "Should Boss the killable bench target")
        self.assertEqual(target.id, self.BUDEW, "Must drag Budew (killable), not Froslass")

    def test_normal_killable_drag_still_fires(self):
        # Regression: a clearly killable, higher-value bench target still gets dragged.
        op_bench = [PokeMock(DRAGAPULT_EX, hp=120)]   # 2-prize, killable at 200
        op_active = PokeMock(65, hp=60)
        target, should = _boss_drag_decision(op_bench, op_active, 6, current_dmg=200)
        self.assertTrue(should)
        self.assertEqual(target.id, DRAGAPULT_EX)


def _run():
    groups = {
        "Item1a_MunkidoriDragPriority": "Item 1a — Munkidori Boss's Orders drag priority",
        "Item1b_CageTrigger": "Item 1b — Battle Cage trigger generalization",
        "Item2_ClefairyPivot": "Item 2 — Clefairy pivot-when-walled",
        "Item3_BossHandSufficiency": "Item 3 — Boss's Orders hand-sufficiency check",
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
