import subprocess
import time
import sys

games = 20

print(f"Running {games} games to collect deck safety fire counts...")
sys.stdout.flush()
open('deck_safety_log.txt', 'w').close()

for i in range(games):
    subprocess.run(["venv/bin/python3", "tools/local_sim_test.py"], capture_output=True, text=True)

with open('deck_safety_log.txt', 'r') as f:
    logs = f.readlines()

counts = {}
for log in logs:
    if "DECK_SAFETY_CHECK:" in log:
        card = log.split("DECK_SAFETY_CHECK: ")[1].split(",")[0].strip()
        counts[card] = counts.get(card, 0) + 1

print("\n--- Fire Counts ---")
for card, count in sorted(counts.items()):
    print(f"{card}: {count} evaluations")
