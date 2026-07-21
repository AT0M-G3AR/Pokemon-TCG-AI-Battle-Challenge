import sys
import json

with open('/Users/garygonzalez/Downloads/87183098.json') as f:
    replay = json.load(f)

print(f"Step 18 Player 1 action: {replay['steps'][18][1].get('action')}")
print(f"Step 19 Player 1 action: {replay['steps'][19][1].get('action')}")
