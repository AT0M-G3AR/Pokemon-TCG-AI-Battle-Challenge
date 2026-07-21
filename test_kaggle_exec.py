import os
import sys
import shutil

# 1. Setup mock environment
base_dir = "/tmp/kaggle_simulations/agent"
if os.path.exists(base_dir):
    shutil.rmtree(base_dir)
os.makedirs(base_dir)

# 2. Extract tarball
os.system(f"tar -xzf agent/submission.tar.gz -C {base_dir}")

# 3. Clean sys.path to strictly mimic a clean Kaggle environment without our local dirs
sys.path = [p for p in sys.path if "Pokemon-TCG-AI-Battle-Challenge" not in p and "agent" not in p and p != ""]

# 4. Change working directory away from the project just to be safe
os.chdir("/tmp")

# 5. Read, compile, and exec main.py exactly like Kaggle does
env = {}
main_path = os.path.join(base_dir, "main.py")

with open(main_path, "r") as f:
    code = f.read()

print("Executing main.py via exec()...")
try:
    code_object = compile(code, main_path, "exec")
    exec(code_object, env)
    print("SUCCESS: agent function loaded ->", "agent" in env)
except Exception as e:
    import traceback
    print("FAILED with traceback:")
    traceback.print_exc()

