import re
with open('agent/policy.py', 'r') as f:
    lines = f.readlines()

new_lines = []
skip = False
for line in lines:
    if "f.write(f\"DECK_SAFETY_CHECK" in line:
        continue
    if "with open('deck_safety_log.txt', 'a') as f:" in line or 'with open("deck_safety_log.txt", "a") as f:' in line:
        continue
    new_lines.append(line)

with open('agent/policy.py', 'w') as f:
    f.writelines(new_lines)
