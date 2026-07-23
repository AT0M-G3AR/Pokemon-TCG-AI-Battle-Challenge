import json
import sys

def parse_replay(file_path):
    with open(file_path, 'r') as f:
        data = json.load(f)
        
    steps = data.get('steps', [])
    
    # We want to reconstruct player 0's hand
    hand = set()
    serial_to_id = {}
    
    for i, step in enumerate(steps):
        if not step:
            continue
            
        obs = step[0]['observation']
        logs = obs.get('logs', [])
        
        for log in logs:
            if 'cardId' in log and 'serial' in log:
                serial_to_id[log['serial']] = log['cardId']
                
            if log.get('playerIndex') != 0:
                continue
                
            t = log.get('type')
            serial = log.get('serial')
            
            if t == 4: # Draw / Added to hand
                hand.add(serial)
            elif t == 6: # MoveCard
                from_area = log.get('fromArea')
                to_area = log.get('toArea')
                if from_area == 2 and to_area != 2:
                    hand.discard(serial)
                elif to_area == 2 and from_area != 2:
                    hand.add(serial)
            elif t == 10: # Put into play / Use Trainer
                if serial in hand:
                    hand.discard(serial)
            elif t == 11: # Attach
                if serial in hand:
                    hand.discard(serial)
            elif t == 12: # Evolve
                if serial in hand:
                    hand.discard(serial)
                    
        # When Poké Pad is played, the next step (or current) asks to select from deck.
        # Let's print out EVERY time player 0 has to make a choice.
        if step[0]['status'] == 'ACTIVE':
            # This is player 0's turn to act
            options = obs.get('options', [])
            if options:
                print(f"--- STEP {i} ---")
                
                hand_ids = [serial_to_id.get(s, f"Unknown-{s}") for s in hand]
                print(f"Hand size: {len(hand)}")
                print(f"Hand Cards: {hand_ids}")
                
                # Try to see if this is a DECK search
                is_deck = any(opt.get('inPlayArea') == 1 or opt.get('area') == 1 for opt in options)
                if is_deck:
                    print("!!! DECK SEARCH !!!")
                    for opt in options:
                        idx = opt.get('index')
                        if idx is not None:
                            print(f" - Option idx {idx} -> cardId: {serial_to_id.get(idx, '?')}")
                print("---")
                
if __name__ == "__main__":
    parse_replay(sys.argv[1])
