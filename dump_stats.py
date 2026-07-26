import sys
import os

sys.path.insert(0, './agent')
from policy import CARD_DB, DUNSPARCE, DUDUNSPARCE, ALAKAZAM
from cg.api import all_attack

attack_db = {a.attackId: a for a in all_attack()}

def print_card_stats(cid):
    c = CARD_DB.get(cid)
    if not c:
        print(f"ID {cid}: NOT FOUND")
        return
    
    print(f"--- {c.name} (ID: {cid}) ---")
    print(f"HP: {c.hp}")
    
    if hasattr(c, 'attacks') and c.attacks:
        for aid in c.attacks:
            att = attack_db.get(aid)
            if att:
                # Format energies if available
                energy_str = "None"
                if hasattr(att, 'energies') and att.energies:
                    # energies is usually a list of int enum values or a list of type names depending on the API structure.
                    energy_str = str(att.energies)
                
                print(f"  Attack: {att.name}")
                print(f"  Cost: {energy_str}")
    else:
        print("  (No attacks)")
    print()

print("== REQUIRED CARD STATS ==")
# 743 Alakazam, 272 Clefairy, 741 Abra, 65 Dunsparce, 66 Dudunsparce
for cid in [ALAKAZAM, 272, 741, DUNSPARCE, DUDUNSPARCE]:
    print_card_stats(cid)
