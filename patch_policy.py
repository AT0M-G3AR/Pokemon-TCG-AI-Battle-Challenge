import re

with open("agent/policy.py", "r") as f:
    content = f.read()

replacement = """
    scores = _sanity_check(obs, options, scores)
    
    # --- Shallow Search Bolt-on ---
    try:
        from shallow_search import shallow_search_pick
        # Only invoke shallow_search_pick to decide between the top static candidates
        best_idx = shallow_search_pick(obs, options, scores, top_n=3, time_limit_sec=2.0)
        if best_idx is not None:
            return [best_idx]
    except Exception as e:
        import traceback
        try:
            with open("/tmp/policy_error.log", "a") as err_log:
                err_log.write(f"--- [SHALLOW SEARCH ERROR] ---\n")
                err_log.write(traceback.format_exc())
                err_log.write("\n")
        except:
            pass
        print(f"[Shallow Search] Error: {e}", flush=True)

    return _pick_best(scores, min_count, max_count)
"""

pattern = r"    scores = _sanity_check\(obs, options, scores\)\n    return _pick_best\(scores, min_count, max_count\)"

new_content = re.sub(pattern, replacement, content)

with open("agent/policy.py", "w") as f:
    f.write(new_content)
