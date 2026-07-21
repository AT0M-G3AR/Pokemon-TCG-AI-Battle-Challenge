import re

with open("agent/policy.py", "r") as f:
    content = f.read()

replacement = """
    # --- Shallow Search Bolt-on ---
    try:
        # NARROW SCOPE: Only run if tiebreak includes ATTACK vs EVOLVE/SUPPORTER
        from cg.api import OptionType
        
        valid = [(i, scores[i]) for i in range(len(options)) if scores[i] > -9000]
        valid.sort(key=lambda x: x[1], reverse=True)
        top_candidates = [v[0] for v in valid[:3]]
        
        has_attack = any(options[idx].type == OptionType.ATTACK for idx in top_candidates)
        has_setup = any(options[idx].type in (OptionType.EVOLVE, OptionType.PLAY) for idx in top_candidates)
        
        if has_attack and has_setup:
            from shallow_search import shallow_search_pick
            best_idx = shallow_search_pick(obs, options, scores, top_n=3, time_limit_sec=2.0)
            if best_idx is not None:
                return [best_idx]
    except Exception as e:
        import traceback
        try:
            with open("/tmp/policy_error.log", "a") as err_log:
                err_log.write("--- [SHALLOW SEARCH ERROR] ---\\n")
                err_log.write(traceback.format_exc())
                err_log.write("\\n")
        except:
            pass
        print(f"[Shallow Search] Error: {e}", flush=True)

    return _pick_best(scores, min_count, max_count)
"""

pattern = r"    # --- Shallow Search Bolt-on ---\n(.*?)return _pick_best\(scores, min_count, max_count\)"

new_content = re.sub(pattern, replacement, content, flags=re.DOTALL)

with open("agent/policy.py", "w") as f:
    f.write(new_content)
