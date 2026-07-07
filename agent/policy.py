"""
PTCG AI Battle Challenge — Policy Logic
AT0M-G3AR | Gary & Team | 2026

ARCHITECTURE:
    select_action() is the single entry point called by main.py.
    It reads the SelectContext from obs_dict and routes to the
    appropriate handler function for that decision type.

    v1: All handlers return random legal selections.
        Structure is in place for v2 heuristic upgrades.

    v2+ (coming): Each handler will score options using board state
        and return the highest-scoring legal selection instead of random.

SELECT CONTEXTS (decision types the engine will ask you to make):
    Deck selection phase:
        "SelectDeck"          — choose your 60-card deck before the game

    Main turn decisions:
        "SelectAttack"        — choose an attack (or pass)
        "SelectEnergyAttach"  — choose which energy to attach and where
        "SelectSupporter"     — choose a Supporter card to play
        "SelectItem"          — choose an Item card to play
        "SelectStadium"       — choose a Stadium card to play
        "SelectRetreat"       — choose to retreat and which Pokémon to switch in
        "SelectBench"         — choose a Pokémon to put on the bench

    Reactive decisions:
        "SelectActive"        — choose which benched Pokémon becomes Active
                                (triggered when Active is KO'd)
        "SelectPrize"         — choose which prize card(s) to take after a KO
        "SelectEvolution"     — choose whether/what to evolve into
        "SelectYesNo"         — binary yes/no choice (coin flip calls, ability triggers)
        "SelectCard"          — generic card selection (search effects, etc.)
        "SelectOrder"         — order cards (e.g. put cards back on deck)
"""

import random


# ─────────────────────────────────────────────────────────────────────────────
# MAIN ROUTER
# ─────────────────────────────────────────────────────────────────────────────

def select_action(obs_dict: dict) -> list[int]:
    """
    Routes the decision to the correct handler based on SelectContext.
    Returns a list of chosen option indices.
    """
    select = obs_dict.get("select")
    if not select:
        return []

    context   = select.get("context", "")
    options   = select.get("option", [])
    min_count = select.get("minCount", 1)
    max_count = select.get("maxCount", 1)

    if not options:
        return []

    # Route by context
    handlers = {
        "SelectDeck":         handle_deck_selection,
        "SelectAttack":       handle_attack,
        "SelectEnergyAttach": handle_energy_attach,
        "SelectSupporter":    handle_supporter,
        "SelectItem":         handle_item,
        "SelectStadium":      handle_stadium,
        "SelectRetreat":      handle_retreat,
        "SelectBench":        handle_bench,
        "SelectActive":       handle_active,
        "SelectPrize":        handle_prize,
        "SelectEvolution":    handle_evolution,
        "SelectYesNo":        handle_yes_no,
        "SelectCard":         handle_card,
        "SelectOrder":        handle_order,
    }

    handler = handlers.get(context, handle_generic)
    return handler(obs_dict, options, min_count, max_count)


# ─────────────────────────────────────────────────────────────────────────────
# HELPER: safe random pick
# ─────────────────────────────────────────────────────────────────────────────

def _random_pick(options: list, count: int) -> list[int]:
    """Pick `count` random indices from the options list."""
    count = max(1, min(count, len(options)))
    return random.sample(list(range(len(options))), count)


def _get_board(obs_dict: dict) -> tuple[dict, dict]:
    """Returns (my_state, opponent_state) from obs_dict."""
    current = obs_dict.get("current", {})
    return current.get("me", {}), current.get("opponent", {})


# ─────────────────────────────────────────────────────────────────────────────
# HANDLERS — v1: all random
# Each function signature is fixed: (obs_dict, options, min_count, max_count)
# Replace the random_pick inside each with scoring logic in v2.
# ─────────────────────────────────────────────────────────────────────────────

def handle_deck_selection(obs_dict, options, min_count, max_count) -> list[int]:
    """
    v1: Return all 60 card IDs as-is (options IS the deck list here).
    The engine provides the legal deck options — we just confirm them.

    v2 TODO: Pre-select our chosen deck by card ID from deck.csv.
    """
    # During deck selection, options contains the card IDs to confirm.
    # Return all indices (the full deck selection).
    return list(range(len(options)))


def handle_attack(obs_dict, options, min_count, max_count) -> list[int]:
    """
    v1: Random attack selection.

    v2 TODO: Score attacks by:
        - Damage output vs opponent's active HP remaining
        - Whether this attack KOs the opponent's active
        - Energy cost efficiency
        - Special effect value (status conditions, bench damage)
        - Prefer attacks that KO > attacks that don't
        - Prefer non-pass options over passing
    """
    # Log for debugging (visible in episode logs on Kaggle)
    my, opp = _get_board(obs_dict)
    active_opp = opp.get("active", {})
    if active_opp:
        opp_name = active_opp.get("name", "?")
        opp_hp   = active_opp.get("hp", "?")
        opp_dmg  = active_opp.get("damage", 0)
        print(f"[SelectAttack] Opponent active: {opp_name} HP:{opp_hp} DMG:{opp_dmg}")

    return _random_pick(options, min_count)


def handle_energy_attach(obs_dict, options, min_count, max_count) -> list[int]:
    """
    v1: Random energy attachment.

    v2 TODO: Score by:
        - Attach to active Pokémon first if it needs energy to attack
        - Attach to benched Pokémon building toward their attack cost
        - Prioritize completing an attack requirement this turn
        - Special energy (Enriching Energy) logic
    """
    return _random_pick(options, min_count)


def handle_supporter(obs_dict, options, min_count, max_count) -> list[int]:
    """
    v1: Random Supporter selection.

    v2 TODO: Score by:
        - Draw supporters (Iono, Professor's Research) when hand is small
        - Search supporters when you need a specific Pokémon
        - Avoid playing supporters that discard good cards
        - Supporter ordering within a turn (play search before draw)
    """
    return _random_pick(options, min_count)


def handle_item(obs_dict, options, min_count, max_count) -> list[int]:
    """
    v1: Random Item selection.

    v2 TODO: Score by:
        - Play Poké Ball variants when bench is empty or needs filling
        - Evolution items when evolution targets are in hand
        - Healing items when active is near KO threshold
    """
    return _random_pick(options, min_count)


def handle_stadium(obs_dict, options, min_count, max_count) -> list[int]:
    """
    v1: Random Stadium selection.

    v2 TODO: Score by:
        - Play our stadium to replace opponent's beneficial stadium
        - Evaluate stadium benefit for current deck strategy
    """
    return _random_pick(options, min_count)


def handle_retreat(obs_dict, options, min_count, max_count) -> list[int]:
    """
    v1: Random retreat decision.

    v2 TODO: Score by:
        - Don't retreat if active can KO opponent next turn
        - Retreat if active is about to be KO'd AND bench has a better attacker
        - Factor in retreat cost vs available energy
        - Consider switching to a Pokémon with more favorable matchup
    """
    return _random_pick(options, min_count)


def handle_bench(obs_dict, options, min_count, max_count) -> list[int]:
    """
    v1: Random bench placement.

    v2 TODO: Score by:
        - Prioritize Pokémon that are part of the main attack line
        - Bench basics needed for evolution chain
        - Avoid benching Pokémon that give opponent easy prizes
        - Fill bench to max (5) when possible for board presence
    """
    return _random_pick(options, min_count)


def handle_active(obs_dict, options, min_count, max_count) -> list[int]:
    """
    v1: Random active Pokémon selection (triggered on KO).

    v2 TODO: Score by:
        - Select benched Pokémon with highest damage output vs current opponent
        - Prefer Pokémon that can attack immediately (energy attached)
        - Avoid sending up weak basics that give easy prizes
        - Consider prize trade — is it worth trading KOs here?
    """
    print(f"[SelectActive] Active was KO'd — choosing replacement from bench")
    return _random_pick(options, min_count)


def handle_prize(obs_dict, options, min_count, max_count) -> list[int]:
    """
    v1: Random prize card selection.

    v2 TODO: Score by:
        - If prize cards are revealed (some effects), pick highest-value card
        - Prefer energy cards if low on energy
        - Prefer key Pokémon if needed for the game plan
    """
    return _random_pick(options, min_count)


def handle_evolution(obs_dict, options, min_count, max_count) -> list[int]:
    """
    v1: Random evolution selection.

    v2 TODO: Score by:
        - Always evolve if evolution completes the attack line
        - Prioritize evolving the active Pokémon first
        - Evolve bench Pokémon building toward the win condition
        - Don't evolve if it resets damage counters strategically
    """
    return _random_pick(options, min_count)


def handle_yes_no(obs_dict, options, min_count, max_count) -> list[int]:
    """
    v1: Random yes/no.

    v2 TODO: Evaluate the specific ability or effect being triggered:
        - Coin flip abilities: usually yes if the upside is worth it
        - Discard-based abilities: depends on hand quality
        - Context-specific logic per card
    """
    return _random_pick(options, min_count)


def handle_card(obs_dict, options, min_count, max_count) -> list[int]:
    """
    v1: Random card selection (generic search effects).

    v2 TODO: Score by:
        - What the search effect is looking for
        - Current hand and board needs
        - Prioritize missing combo pieces
    """
    return _random_pick(options, min_count)


def handle_order(obs_dict, options, min_count, max_count) -> list[int]:
    """
    v1: Random card ordering (e.g. putting cards back on deck).

    v2 TODO: Score by:
        - Put high-priority cards on top if given the choice
        - Put cards you don't need soon on bottom
    """
    return _random_pick(options, min_count)


def handle_generic(obs_dict, options, min_count, max_count) -> list[int]:
    """
    Catch-all for any context not explicitly handled above.
    Logs the unknown context so we can add a handler for it.
    """
    select  = obs_dict.get("select", {})
    context = select.get("context", "UNKNOWN")
    print(f"[UNHANDLED CONTEXT: {context}] Falling back to random pick.")
    return _random_pick(options, min_count)
