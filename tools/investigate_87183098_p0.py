import sys
import json
with open('/Users/garygonzalez/Downloads/87183098.json') as f:
    replay = json.load(f)

for step_idx in [17, 18, 19]:
    print(f"Step {step_idx} Player 0 action: {replay['steps'][step_idx][0].get('action')}")
