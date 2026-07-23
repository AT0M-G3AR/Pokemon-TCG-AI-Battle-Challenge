import json

path = "venv/lib/python3.11/site-packages/kaggle_environments/envs/cabt/cabt.json"
with open(path) as f:
    data = json.load(f)
    for card in data.get('cards', []):
        if card.get('id') == 272:
            print(json.dumps(card, indent=2))
        elif 'Clefairy ex' in card.get('name', ''):
            print(f"Found other Clefairy: {card['id']} - {card['name']}")
