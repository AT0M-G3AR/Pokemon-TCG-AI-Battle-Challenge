import json
import sys

def debug_replay(file_path):
    with open(file_path, 'r') as f:
        data = json.load(f)
        
    steps = data.get('steps', [])
    step = steps[18]
    obs = step[0].get('observation', {})
    select = obs['select']
    deck = select['deck']
    options = select['option']
    
    print("Available options for Poké Pad:")
    for opt in options:
        idx = opt['index']
        card = deck[idx]
        print(f" - Option idx {idx} -> cardId: {card['id']} (serial: {card['serial']})")
        
    # Also we want to reconstruct the hand to confirm if Dudunsparce was already in hand!
    # I already have parse_hand.py which tracks hand. Let's merge that logic.
    hand = set()
    for i in range(19): # up to step 18
        obs_log = steps[i][0].get('observation', {}).get('logs', [])
        for log in obs_log:
            if log.get('playerIndex') != 0: continue
            t = log.get('type')
            serial = log.get('serial')
            if t == 4: hand.add(serial)
            elif t == 6:
                if log.get('fromArea') == 2 and log.get('toArea') != 2: hand.discard(serial)
                elif log.get('toArea') == 2 and log.get('fromArea') != 2: hand.add(serial)
            elif t in (10, 11, 12):
                if serial in hand: hand.discard(serial)
                
    print(f"Hand Serials at Step 18: {hand}")
    
    # map serial to id
    serial_to_id = {}
    for i in range(19):
        obs_log = steps[i][0].get('observation', {}).get('logs', [])
        for log in obs_log:
            if 'cardId' in log and 'serial' in log:
                serial_to_id[log['serial']] = log['cardId']
                
    hand_ids = [serial_to_id.get(s, f"Unknown-{s}") for s in hand]
    print(f"Hand card IDs: {hand_ids}")

if __name__ == "__main__":
    debug_replay(sys.argv[1])
