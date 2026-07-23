import os
import re

with open('agent/policy.py', 'r') as f:
    content = f.read()

# Replace any instance of `with open("...") as f: f.write(...); score += ...`
# with multi-line equivalent
def repl(m):
    indent = m.group(1)
    card = m.group(2)
    deck = m.group(3)
    score_line = m.group(4)
    return f"{indent}with open('deck_safety_log.txt', 'a') as f:\n{indent}    f.write(f\"DECK_SAFETY_CHECK: {card}, deck={{{deck}}}\\n\")\n{indent}{score_line}"

# For single quotes (Dudunsparce, etc, though I did them on separate lines)
content = re.sub(r'([ \t]+)with open\("deck_safety_log.txt", "a"\) as f: f.write\(f"DECK_SAFETY_CHECK: ([^,]+), deck=\{([^}]+)\}\\n"\); (score \+= [^\n]+)', repl, content)

with open('agent/policy.py', 'w') as f:
    f.write(content)
