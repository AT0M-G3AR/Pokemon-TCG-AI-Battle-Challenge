import inspect
import os
import sys

code = """
import inspect
import os
import sys

frame = inspect.currentframe()
if frame:
    current_file = inspect.getframeinfo(frame).filename
    agent_dir = os.path.dirname(os.path.abspath(current_file))
    print("Detected agent_dir:", agent_dir)
"""

code_object = compile(code, "/tmp/kaggle_simulations/agent/main.py", "exec")
exec(code_object, {})
