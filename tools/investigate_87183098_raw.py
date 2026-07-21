import sys
import json

with open('/Users/garygonzalez/Downloads/87183098.json') as f:
    replay = json.load(f)

for step_idx in [17, 18, 19]:
    print(f"\n==== STEP {step_idx} ====")
    obs = replay['steps'][step_idx][1].get('observation')
    print("Agent Options from JSON:")
    for i, opt in enumerate(obs.get('select', {}).get('option', [])):
        print(f"  {i}: {opt}")
    
    print(f"Action in JSON: {replay['steps'][step_idx][1].get('action')}")
