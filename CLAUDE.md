# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Our submission for the **Pokémon TCG AI Battle Challenge** (Kaggle × The Pokémon Company × HEROZ × Matsuo Institute). Two tracks, both required for prizes:
- **Simulation** (deadline Aug 16, 2026): an AI agent that plays PTCG on Kaggle's `cabt` Elo ladder. Code lives in `agent/`.
- **Strategy** (deadline Sep 13, 2026): a written report in `writeup/`.

The submitted artifact is a single function `agent(obs_dict: dict) -> list[int]` that the `cabt` engine calls for every decision, returning the chosen legal option index/indices.

> **Note on stale docs:** `README.md` and `TEAM_ONBOARDING.md` describe an older Dragapult/Blaziken deck. The **current, actual deck is Alakazam + Dudunsparce** (see `agent/deck.csv` and `research/deck_theory.md`). Trust `deck.csv`, `policy.py`, and git log over the README when they disagree.

## Common commands

All Python must run under the project venv (Python **3.11** — the `cg` engine's compiled `.so`/`.dylib` are built for it). Run from repo root.

```bash
# Run a full local game (agent vs. agent), validate every step, save replay
venv/bin/python tools/local_sim_test.py
# → prints per-step context/options, flags EMPTY/OUT-OF-BOUNDS/EXCEPTION,
#   writes replay_debug.html. "✅ NO ERRORS — Safe to submit" gate at the end.

# Batch smoke test (runs local_sim_test N times, checks for crashes)
bash run_batch.sh                      # → tools/batch_test_regression.py

# Build the submission tarball (runs a py_compile pre-flight first)
bash agent/build_submission.sh         # → agent/submission.tar.gz
#   Then upload manually via the Kaggle Submissions tab. 5 submissions/day;
#   only the 2 most recent are active on the ladder.

# View a replay
python3 -m http.server 8080            # then open http://localhost:8080/replay_debug.html
```

**Single-scenario / regression tests** are standalone scripts, not a pytest suite. Each `agent/verify_v3XX.py` and `agent/audit_*.py` builds mock `Obs`/`Player`/`Card` objects (see the classes at the top of any `verify_*.py`) and asserts a handler returns the right option. Run one directly:

```bash
venv/bin/python agent/verify_v347.py   # or whichever version you're validating
```

When you change policy logic, add/extend a `verify_v3XX.py` capturing the exact board state that motivated the change, then confirm `local_sim_test.py` still reports NO ERRORS before building.

**macOS gotcha:** if the `cg` native libs are blocked by Gatekeeper, clear the quarantine attr (`xattr -d com.apple.quarantine agent/cg/*.dylib`). `build_submission.sh` sets `COPYFILE_DISABLE=1` so no `._*` resource-fork files pollute the tarball.

## Architecture

### Decision flow
```
cabt engine → agent(obs_dict)            agent/main.py
   → to_observation_class(obs_dict)      → typed Observation (cg/api.py)
   → select_action(obs)                  agent/policy.py  (the ROUTER)
       → dispatch on obs.select.context (a SelectContext enum)
       → handle_<context>(obs, options, min_count, max_count) → list[int]
```

- **`agent/main.py`** — thin entry point. Resolves its own directory via `inspect` because **`__file__` is undefined in Kaggle's `exec()` sandbox** (don't "fix" this). When `obs.select is None` the engine is asking for the deck → returns the 60 card IDs from `deck.csv`. Wraps everything in try/except returning `[0]` so the agent can never crash the match.
- **`agent/policy.py`** (~2000 lines, the core) — `select_action()` maps each `SelectContext` (MAIN, TO_HAND, ATTACH_TO, EVOLVE, DAMAGE_COUNTER, …) to a `handle_*` function. Any unmapped context or handler exception falls back to `_safe_fallback` (random legal pick) and logs to `/tmp/policy_error.log`. **`handle_main` is the most important handler** — it decides play/attack sequencing each turn.
- **`agent/search_api.py`** — wraps the engine's Search API (`lib.SearchBegin`/`SearchStep`/`SearchEnd`) to *simulate* a turn and read the exact resulting hand size, plus pure-math damage helpers. Used to compute lethal precisely instead of estimating. Always falls back to `hand_size * 20` math if the search call fails.
- **`agent/cg/`** — vendored `cabt` engine bindings (`api.py` typed dataclasses + enums, `sim.py` ctypes loader, and the platform `.so`/`.dylib`/`.dll`). This directory is **shipped inside the submission tarball**. Treat as a read-only dependency.

### The deck's win condition (drives every scoring decision)
Alakazam's **Powerful Hand** places `hand_size * 20` damage as **damage counters** (not attack damage), so it ignores Weakness/Resistance and is uncapped. Consequences baked into the policy — keep them intact:
1. **Compute lethal before playing any card, then STOP.** Every card played from hand lowers damage by 20. `handle_main` checks lethal first.
2. **Dudunsparce "Run Away Draw" is top priority** (score ~15000) — draws 3 and shuffles itself back, inflating hand without deck-out risk.
3. **Mist Energy (ID 11) nullifies Powerful Hand** (it's an effect, not damage). Enhanced Hammer (1081) must strip it before attacking — see the mist check in `evaluate_attack`.
4. **Deck-safety brake:** when the deck is nearly empty and the hand is already lethal, stop drawing (search `DECK_SAFETY_FIRED`).

### Conventions
- **Card identity is by integer ID.** Named constants live at the top of `policy.py` (e.g. `ALAKAZAM=743`, `DUDUNSPARCE=66`, `MIST_ENERGY=11`, `ENH_HAMMER=1081`). Add a constant rather than hardcoding a magic number; `all_card_data()` → `CARD_DB` gives full card stats by ID. The complete pool is in `research/full_card_pool.txt`.
- **Handlers return option *indices*, never cards** — indices into the `options` list the engine supplied, respecting `min_count`/`max_count`.
- **Scoring is tiered with large magnitudes** (e.g. 50000 instant-win > 20000 game-winning KO > 18000 KO > … > 3000 weak attack). New behavior slots into that ladder; see `evaluate_attack` and `handle_main`'s scoring for the scale.
- **Versioning:** work is tagged `v3.XX` in commit messages and mirrored in verify/audit script names. The header docstring in `policy.py` states the current version and active rules — update it when behavior changes.
- **`research/`** holds the domain knowledge the policy encodes (`deck_theory.md`, `meta_analysis.md`, `card_notes.md`, matchup docs). Read these before changing matchup logic. `dataset/*.csv` are meta/matchup stats for the writeup.
- Root-level `dump_*.py`, `investigate_*.py`, `print_*.py`, and `*_log.txt` are one-off replay-debugging scratch — safe to ignore; the `86*.json` / `87*.json` / `88*.json` files are downloaded match replays.
