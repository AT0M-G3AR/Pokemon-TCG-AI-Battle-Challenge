# Card Interaction Notes

Key cards and interactions the agent policy must explicitly handle.

## Trainer Cards
*[Draw supporters, search cards, energy acceleration — priority order for the agent]*

## Pokémon Abilities
*[Abilities that trigger at specific times — agent must recognize these contexts]*

## Energy Cards
*[Special energy interactions — Enriching Energy, Mist Energy, etc.]*

## Edge Cases
*[Coin flips, status conditions, retreat rules — any non-obvious simulator behavior]*

## Critical Safety Rules for Abilities

### Teleporter (Abra 109)
- NEVER activate if bench is completely empty — instant loss
- Only activate if bench has at least 1 Pokémon to promote
- Score: 11000 with bench, -9999 without bench

### Run Away Draw (Dudunsparce 66)  
- NEVER activate if already lethal (reduces hand size)
- Safe to use anytime bench has space to promote Alakazam
