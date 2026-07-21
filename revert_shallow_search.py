import re

with open("agent/policy.py", "r") as f:
    content = f.read()

pattern = r"    # --- Shallow Search Bolt-on ---\n.*?return _pick_best\(scores, min_count, max_count\)"
replacement = "    return _pick_best(scores, min_count, max_count)"

new_content = re.sub(pattern, replacement, content, flags=re.DOTALL)

with open("agent/policy.py", "w") as f:
    f.write(new_content)
