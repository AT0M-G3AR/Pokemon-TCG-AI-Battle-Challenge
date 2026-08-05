"""
v3.51 ladder monitor. Overall W/L/D + the Item-1 fix check:
in games where Alakazam is walled 2+ OUR-turns (the commit trigger), does Clefairy
now get energized toward attack-ready (2 energy) / land Full Moon Rondo? — vs the
v3.50 baseline where she stayed at 0 energy in every walled game.
    venv/bin/python tools/monitor_v351.py
"""
import os, json, concurrent.futures
from kaggle.api.kaggle_api_extended import KaggleApi

SUB = 55251552           # v3.51
BASELINE_SUB = 55197599  # v3.50
COMP = "pokemon-tcg-ai-battle"
CLEF = 272; ALA = 743; MIST = 11
BLOCKERS = {28, 74, 117, 203, 207, 362, 414, 835}   # DAMAGE_BLOCKING_ABILITY_IDS
WALL_THRESHOLD = 2   # >= this many walled within the window
WALL_WINDOW = 4      # v3.52 Item 1c: windowed, not strictly-consecutive (matches policy)
SCR = "/private/tmp/claude-501/-Users-garygonzalez/b341e299-c5c6-471d-9559-9ad30c084b9e/scratchpad/v351mon"
os.makedirs(SCR, exist_ok=True)


def energy_ids(pk):
    return [e.get("id") for e in (pk.get("energyCards", []) or []) if isinstance(e, dict)]


def main():
    api = KaggleApi(); api.authenticate()
    meta = {}
    for e in api.competition_list_episodes(SUB):
        a = next((x for x in (e.agents or []) if x.submission_id == SUB), None)
        if a is None or a.reward is None:
            continue
        meta[e.id] = (a.index, a.reward)

    w = sum(1 for _, r in meta.values() if r > 0)
    l = sum(1 for _, r in meta.values() if r < 0)
    d = sum(1 for _, r in meta.values() if r == 0)
    decided = w + l + d
    scores = {}
    for s in api.competition_submissions(COMP):
        ref = getattr(s, "ref", None)
        if ref in (SUB, BASELINE_SUB):
            scores[ref] = getattr(s, "public_score", None)
    print(f"GAMES={decided}  RECORD {w}-{l}-{d}" + (f"  winrate={w/decided:.0%}" if decided else ""))
    print(f"SCORE v3.51={scores.get(SUB,'?')}  v3.50_baseline={scores.get(BASELINE_SUB,'?')}")

    def dl(eid):
        p = os.path.join(SCR, f"episode-{eid}-replay.json")
        if os.path.exists(p) and os.path.getsize(p) > 1000:
            return eid
        try:
            api.competition_episode_replay(eid, path=SCR, quiet=True); return eid
        except Exception:
            return None
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as ex:
        got = [r for r in ex.map(dl, list(meta)) if r]

    eligible = []   # (eid, result, walled_turns, clef_max_energy, clef_attacks)
    for eid in got:
        oi, r = meta[eid]
        try:
            data = json.load(open(os.path.join(SCR, f"episode-{eid}-replay.json")))
        except Exception:
            continue
        st_ = data["steps"]; opp = 1 - oi
        turn_walled = {}; clef_max_e = 0; clef_atk = 0; seen = set()
        for si in range(len(st_)):
            for ai in (0, 1):
                o = st_[si][ai].get("observation") or {}
                cur = o.get("current")
                if cur:
                    me = cur["players"][oi]; op = cur["players"][opp]
                    if cur.get("yourIndex") == oi:
                        my_act = [x for x in me.get("active", []) if x]
                        op_act = [x for x in op.get("active", []) if x]
                        ala = my_act and my_act[0].get("id") == ALA
                        blk = any((p.get("id") in BLOCKERS) for p in
                                  ([x for x in op.get("active", []) if x] + [x for x in op.get("bench", []) if x]))
                        mist = op_act and MIST in energy_ids(op_act[0])
                        t = cur.get("turn")
                        turn_walled[t] = turn_walled.get(t, False) or bool(ala and (blk or mist))
                    for pk in [x for x in me.get("active", []) if x] + [x for x in me.get("bench", []) if x]:
                        if pk.get("id") == CLEF:
                            clef_max_e = max(clef_max_e, len(energy_ids(pk)))
                for L in (o.get("logs") or []):
                    if L.get("serial") in seen: continue
                    seen.add(L.get("serial"))
                    if L.get("type") == 15 and L.get("playerIndex") == oi and L.get("cardId") == CLEF:
                        clef_atk += 1
        # v3.52 Item 1c: windowed eligibility — >= THRESHOLD walled within any WINDOW of
        # consecutive OUR-turns (matches _update_clefairy_commitment's sliding window).
        seq = [turn_walled[t] for t in sorted(turn_walled)]
        n_walled = sum(1 for x in seq if x)
        eligible_flag = any(sum(1 for x in seq[i:i + WALL_WINDOW] if x) >= WALL_THRESHOLD
                            for i in range(len(seq)))
        if eligible_flag:
            eligible.append((eid, "W" if r > 0 else "L", n_walled, clef_max_e, clef_atk))

    print(f"COMMIT-ELIGIBLE (>= {WALL_THRESHOLD} walled within any {WALL_WINDOW}-our-turn window): {len(eligible)}  <-- the real sample")
    if eligible:
        e1 = sum(1 for g in eligible if g[3] >= 1)
        e2 = sum(1 for g in eligible if g[3] >= 2)
        atk = sum(1 for g in eligible if g[4] > 0)
        print(f"    Clefairy energized >=1: {e1}/{len(eligible)}  |  reached 2 (attack-ready): {e2}/{len(eligible)}  |  "
              f"landed Full Moon Rondo: {atk}/{len(eligible)}   (v3.50 baseline: 0 energized, 0 attacks)")
    for eid, res, wt, ce, ca in eligible:
        print(f"    ep {eid} [{res}]: walled_turns={wt}  clef_max_energy={ce}  clef_attacks={ca}")
    print(f"::DECIDED={decided}::COMMIT_ELIGIBLE={len(eligible)}::")


if __name__ == "__main__":
    main()
