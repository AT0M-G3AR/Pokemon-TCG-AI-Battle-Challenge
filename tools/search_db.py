import sys, os
sys.path.insert(0, os.path.abspath('agent'))
from cg.api import all_card_data

for c in all_card_data():
    if hasattr(c, 'abilities'):
        for a in c.abilities:
            if "Draw" in a.name or "draw" in a.text.lower():
                print(f"Card {c.name} (ID: {c.cardId}) - Ability: {a.name} -> {a.text}")
