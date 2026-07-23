import json
import sys

def debug_replay(file_path):
    with open(file_path, 'r') as f:
        data = json.load(f)
        
    steps = data.get('steps', [])
    for i, step in enumerate(steps):
        if not step: continue
        
        status0 = step[0].get('status')
        status1 = step[1].get('status')
        print(f"Step {i}: p0_status={status0}, p1_status={status1}")
        
        # Check where options are
        for p_idx in [0, 1]:
            obs = step[p_idx].get('observation', {})
            has_options = 'options' in obs
            select = obs.get('select')
            has_select_options = False
            if select and 'options' in select:
                has_select_options = True
            
            if has_options or has_select_options:
                print(f"  Player {p_idx} has options! obs.options: {has_options}, obs.select.options: {has_select_options}")
                
        if i > 20:
            break

if __name__ == "__main__":
    debug_replay(sys.argv[1])
