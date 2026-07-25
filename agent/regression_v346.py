import sys, os
from kaggle_environments import make

sys.path.insert(0, os.path.dirname(__file__))
import importlib.util

spec = importlib.util.spec_from_file_location('main_mod', 'main.py')
main_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(main_mod)

print("Running 20 self-play games for v3.46 regression...")

for i in range(20):
    env = make('cabt')
    steps = env.run([main_mod.agent, main_mod.agent])
    # Just need it to not crash
    if (i+1) % 5 == 0:
        print(f"Completed {i+1}/20 games.")

print("All 20 games completed without crashes.")
