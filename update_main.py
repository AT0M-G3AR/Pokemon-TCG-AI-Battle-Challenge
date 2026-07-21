import sys

with open("agent/main.py", "r") as f:
    content = f.read()

new_content = """import os
import sys

# Ensure Kaggle simulation agent directory is in sys.path so local imports work
agent_dir = "/kaggle_simulations/agent"
if os.path.exists(agent_dir) and agent_dir not in sys.path:
    sys.path.insert(0, agent_dir)
elif os.getcwd() not in sys.path:
    sys.path.insert(0, os.getcwd())

""" + content.split("import os\n")[1]

with open("agent/main.py", "w") as f:
    f.write(new_content)
