import sys
import re

with open("agent/main.py", "r") as f:
    content = f.read()

new_deck_logic = """file_path = "deck.csv"
if not os.path.exists(file_path):
    file_path = os.path.join(agent_dir, "deck.csv")
if not os.path.exists(file_path):
    file_path = "/kaggle_simulations/agent/deck.csv"
"""

pattern = re.compile(r"file_path = \"deck\.csv\".*?(?=\nwith open)", re.DOTALL)
new_content = pattern.sub(new_deck_logic, content)

with open("agent/main.py", "w") as f:
    f.write(new_content)
