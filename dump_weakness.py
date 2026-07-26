import sys
sys.path.insert(0, './agent')
from policy import CARD_DB, DUNSPARCE, DUDUNSPARCE, ALAKAZAM

# 743 Alakazam, 272 Clefairy, 741 Abra, 65 Dunsparce, 66 Dudunsparce
card_ids = [ALAKAZAM, 272, 741, DUNSPARCE, DUDUNSPARCE]

print("== REQUIRED CARD WEAKNESS/RESISTANCE ==")
for cid in card_ids:
    c = CARD_DB.get(cid)
    if not c:
        print(f"ID {cid}: NOT FOUND")
        continue
    
    weakness_str = str(getattr(c, 'weakness', 'None'))
    resistance_str = str(getattr(c, 'resistance', 'None'))
    
    print(f"--- {c.name} (ID: {cid}) ---")
    print(f"HP: {c.hp}")
    print(f"Weakness: {weakness_str}")
    print(f"Resistance: {resistance_str}")
    print()
