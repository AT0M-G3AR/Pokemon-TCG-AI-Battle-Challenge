import subprocess

found = False
for i in range(50):
    print(f"Running game {i+1}...")
    result = subprocess.run(["venv/bin/python3", "tools/local_sim_test.py"], capture_output=True, text=True)
    if "HANDLE TO DECK FIRED" in result.stdout:
        print("Success! Found 'HANDLE TO DECK FIRED' in local sim!")
        print("Count:", result.stdout.count("HANDLE TO DECK FIRED"))
        found = True
        break

if not found:
    print("Ran 50 games, but Sacred Ash was never played. That's RNG for you.")
