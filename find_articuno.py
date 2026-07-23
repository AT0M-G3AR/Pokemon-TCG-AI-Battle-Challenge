import json

def get_opponent_cards(filename):
    with open(filename, 'r') as f:
        data = json.load(f)
    
    unique_ids = set()
    for step in data['steps']:
        if not step or len(step) == 0: continue
        obs = step[0].get('observation', {})
        if obs and obs.get('current') and 'players' in obs['current']:
            p1 = obs['current']['players'][1]
            for act in p1.get('active', []):
                if act:
                    unique_ids.add(act['id'])
            for bench_poke in p1.get('bench', []):
                if bench_poke:
                    unique_ids.add(bench_poke['id'])
                    
    print("Opponent card IDs:", unique_ids)

get_opponent_cards('87283592.json')
