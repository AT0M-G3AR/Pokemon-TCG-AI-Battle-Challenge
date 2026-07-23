import subprocess
import time
import sys

games = 0
fires = 0

print("Running batch test to find Sacred Ash triggers...")
sys.stdout.flush()

for i in range(100):
    games += 1
    result = subprocess.run(["venv/bin/python3", "tools/local_sim_test.py"], capture_output=True, text=True)
    count = result.stdout.count("HANDLE TO DECK FIRED")
    if count > 0:
        fires += count
        print(f"Game {games}: Found {count} fires! Total fires: {fires}")
        sys.stdout.flush()
    if fires >= 5:
        break

print(f"Finished: {fires} Sacred Ash triggers in {games} games.")
sys.stdout.flush()
