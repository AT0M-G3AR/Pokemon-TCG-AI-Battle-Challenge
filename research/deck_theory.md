# Deck Theory: Alakazam + Dudunsparce Engine

## Core Deck Identity
This deck is a highly synergistic **hand-inflation engine**. Its goal is to maximize the number of cards in hand to fuel Alakazam's *Powerful Hand* attack, which places 2 damage counters on the opponent's Active Pokémon for every card in the user's hand. Because it places *damage counters* rather than dealing direct damage, it ignores Weakness, Resistance, and many protective effects, while offering completely uncapped damage potential.

### The Draw Engine
The heart of the deck is **Dudunsparce (ID 66)**. 
- **Ability (Run Away Draw):** Once during your turn, draw 3 cards, then shuffle Dudunsparce and all attached cards back into the deck.
- **Synergy:** By using this ability every turn, the hand size inflates rapidly without the risk of decking out (since the Dudunsparce line shuffles back in to be searched out again). 

### The Evolution Line
- **Abra (741) -> Kadabra (742) -> Alakazam (743)**
- **Kadabra's Psychic Draw:** When evolving from hand, you may draw 2 cards. This bridges directly into the Alakazam setup and gives an extra hand-size boost. Evolving through Kadabra is almost always strictly better than using Rare Candy.
- **Alakazam's Powerful Hand:** Cost: [1 Psychic]. Effect: Place 2 damage counters for each card in your hand.

### Key Tech and Supporters
- **Enhanced Hammer (1081):** Essential. Since *Powerful Hand* places damage counters, it is completely blocked by effect-preventing special energies like Mist Energy. Enhanced Hammer removes these before attacking.
- **Dawn (1231) & Hilda (1225):** Core search supporters to thin the deck and assemble the combo pieces.
- **Enriching Energy (ACE SPEC):** Draws 4 cards when attached.

---

## Agent Strategy & Pilot Guidelines

### Phase 1 — Setup (Turns 1-2)
- Go FIRST. The deck needs the extra turn to evolve its Stage 2 line and get Dudunsparce active.
- Prioritize Buddy-Buddy Poffin to bench Abra and Dunsparce.
- Use Dawn/Hilda to pull the exact missing pieces.

### Phase 2 — The Engine (Turns 3+)
- **Activate Abilities:** Spam Dudunsparce's *Run Away Draw*. Spam Kadabra's *Psychic Draw* on evolution.
- **Lethal Calculation:** The AI must track `hand_size * 20`. Once this value equals or exceeds the opponent Active's HP, **STOP playing cards from the hand**. Every card played reduces damage output by 20.
- **Deck Preservation:** If the deck size gets dangerously low (close to the remaining number of prizes) AND the hand is already lethal, **stop drawing**. Do not use Dudunsparce or Poke Pads. Preserve the deck to win.

---

## Why This Deck for AI Piloting
- **No Complex Energy Math:** Alakazam only needs 1 Psychic energy to swing.
- **Synergistic Loops:** The Dudunsparce loop is easy for an agent to execute on cooldown.
- **Target Selection:** *Powerful Hand* only hits the Active Pokémon, removing the complex branching logic required for spread damage (like Dragapult's Phantom Dive).

---

## Matchup Notes

| Opponent | Expected | Key Note |
|---|---|---|
| Crustle | Favorable | Crustle blocks ex attacks, but Alakazam is a single-prize non-ex attacker. |
| Mist Energy Decks | Variable | Must use Enhanced Hammer immediately. If out of Hammers, you must wait out the Mist Energy or Boss around it. |
| Spread Decks (Dragapult) | Even | Dragapult hits the bench. We must rely on our 140 HP surviving the initial hits, or play Battle Cage (1264) to block bench damage counters. |
