import sys
import re

with open("agent/main.py", "r") as f:
    content = f.read()

# Remove old sys.path logic and replace with inspect logic
new_logic = """import inspect

# Bulletproof path resolution for Kaggle's exec() environment
# __file__ is not defined, and os.getcwd() might be the wrong directory.
frame = inspect.currentframe()
if frame:
    current_file = inspect.getframeinfo(frame).filename
    agent_dir = os.path.dirname(os.path.abspath(current_file))
    if agent_dir not in sys.path:
        sys.path.insert(0, agent_dir)
"""

# Replace the block from "import os" up to "import random"
pattern = re.compile(r"import os\nimport sys.*?(?=import random)", re.DOTALL)
new_content = pattern.sub("import os\nimport sys\n" + new_logic + "\n", content)

with open("agent/main.py", "w") as f:
    f.write(new_content)
