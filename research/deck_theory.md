# Deck Theory — Dragapult ex / Blaziken ex

## Deck List (v2)
| Card | Count | ID |
|---|---|---|
| Dreepy | 4 | 119 |
| Drakloak | 3 | 120 |
| Dragapult ex | 3 | 121 |
| Torchic | 2 | 324 |
| Combusken | 1 | 325 |
| Blaziken ex | 2 | 326 |
| Buddy-Buddy Poffin | 4 | 1086 |
| Night Stretcher | 2 | 1097 |
| Poké Pad | 3 | 1152 |
| Rare Candy | 3 | 1079 |
| Switch | 2 | 1123 |
| Ultra Ball | 4 | 1121 |
| Unfair Stamp | 1 | 1080 |
| Risky Ruins | 1 | 1260 |
| Team Rocket's Watchtower | 1 | 1256 |
| Boss's Orders | 2 | 1182 |
| Colress's Tenacity | 2 | 1194 |
| Crispin | 2 | 1198 |
| Dawn | 2 | 1231 |
| Lillie's Determination | 4 | 1227 |
| Basic Psychic Energy | 6 | 5 |
| Basic Fire Energy | 6 | 2 |

## Win Condition
Dragapult ex's Phantom Dive deals 200 damage to the opponent's Active
and spreads 50 damage to 2 of their Benched Pokémon. The strategy is
to use Phantom Dive repeatedly to set up KOs across the opponent's
entire field simultaneously — KOing the active while the spread damage
puts bench targets into KO range for subsequent turns.

## Two-Phase Game Plan

### Phase 1 — Setup (Turns 1-3)
- Bench Dreepy x2 minimum using Buddy-Buddy Poffin + Ultra Ball
- Bench Torchic for Blaziken ex acceleration engine
- Draw with Lillie's Determination and Colress's Tenacity
- Attach Psychic energy to Dreepy/Drakloak
- Evolve with Rare Candy: Dreepy → Dragapult ex (skip Drakloak)

### Phase 2 — Sweep (Turns 3+)
- Blaziken ex Ability: attach 2 Fire energy from discard each turn
- Dawn: move energy from bench to active Dragapult ex
- Crispin: recover 2 Basic energy from discard
- Phantom Dive every turn — 200 active + 50+50 bench spread
- Boss's Orders: pull high-value benched targets into active
- Chain KOs — bench targets damaged by spread become easy prizes

## Why This Deck for AI Piloting
- Single clear win condition: Phantom Dive every turn
- Linear decision tree: evolve → attach energy → attack
- Blaziken energy acceleration is mechanical and rule-encodable
- Spread targeting (DAMAGE_COUNTER context) is the main skill expression
- Verified playable on TCG Live — real competitive viability confirmed

## Matchup Notes
| Opponent | Expected | Key Note |
|---|---|---|
| Dragapult mirror | Even | Speed of setup determines winner |
| Crustle | Favorable | Phantom Dive is not an ex attack |
| Bellibolt ex | Favorable | Spread punishes benched Tynamo |
| Mega Lucario ex | Favorable | Psychic weakness on Riolu line |

## Agent Priority Rules (feeds into policy.py)
1. Always evolve when evolution target is in hand
2. Always attach energy — Psychic to Dragapult line, Fire to Blaziken line
3. Always use Phantom Dive when Dragapult ex has 2 Psychic attached
4. Target bench slots with highest combined HP + prize value
5. Use Boss's Orders when opponent has a high-value benched Pokémon
6. Play Lillie's Determination / Colress's Tenacity when hand < 4 cards
7. Use Rare Candy only on Dreepy (never on Drakloak)
