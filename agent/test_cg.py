from cg.api import all_card_data, all_attack

cards = all_card_data()
attacks = {a.attackId: a for a in all_attack()}

for c in cards:
    if c.cardId == 414:
        print(f"ID {c.cardId}: {c.name}, HP: {c.hp}")
        for aid in c.attacks:
            atk = attacks.get(aid)
            if atk:
                print(f"  Attack: {atk.name}, Damage: {atk.damage}, Text: {atk.text}")



