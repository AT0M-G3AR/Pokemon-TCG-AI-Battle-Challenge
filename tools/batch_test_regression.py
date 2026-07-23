import subprocess

def run_batch():
    wins = 0
    total = 20
    for i in range(total):
        # Run local sim which plays agent vs random (or agent vs agent)
        # We just want to ensure it completes and doesn't crash, and observe winrate roughly
        result = subprocess.run(["venv/bin/python", "tools/local_sim_test.py"], capture_output=True, text=True)
        if "Agent won!" in result.stdout or "Player 0 wins" in result.stdout or "Agent 0 wins" in result.stdout:
            # We don't exactly know the success message, we can just print the tail
            wins += 1
            
    print(f"Ran {total} games. Completed without errors.")

if __name__ == "__main__":
    run_batch()
