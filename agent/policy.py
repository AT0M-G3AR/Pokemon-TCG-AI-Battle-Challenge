"""
PTCG AI Battle Challenge — Policy Logic
AT0M-G3AR | Gary & Team | 2026

Uses the typed Observation object from cg.api (official interface).

ARCHITECTURE:
    select_action(obs) is the single entry point called by main.py.
    Routes by obs.select.context to the appropriate handler.

    v1: All handlers return random legal selections.
        Full scaffold in place for v2 heuristic upgrades.

    v2+ (coming): Each handler scores options using board state
        and returns the best legal selection.

SELECT CONTEXTS:
    Deck:     None (handled in main.py — returns deck IDs directly)
    Attack:   SelectAttack
    Energy:   SelectEnergyAttach
    Trainer:  SelectSupporter, SelectItem, SelectStadium
    Movement: SelectRetreat, SelectBench, SelectActive
    Reaction: SelectPrize, SelectEvolution, SelectYesNo, SelectCard, SelectOrder
"""

import random


# ─────────────────────────────────────────────────────────────────────────────
# MAIN ROUTER
# ─────────────────────────────────────────────────────────────────────────────

def select_action(obs) -> list[int]:
    """
    Routes the decision to the correct handler based on SelectContext.

    Args:
        obs: Typed Observation object from cg.api.to_observation_class()
             obs.select.context  — decision type string
             obs.select.option   — list of legal options
             obs.select.minCount — minimum number of indices to return
             obs.select.maxCount — maximum number of indices to return
             obs.current         — full board state (me + opponent)

    Returns:
        list[int]: indices of chosen options (no duplicates, within bounds)
    """
    context   = obs.select.context
    options   = obs.select.option
    min_count = obs.select.minCount
    max_count = obs.select.maxCount

    if not options:
        return []

    handlers = {
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
    return handler(obs, options, min_count, max_count)


# ─────────────────────────────────────────────────────────────────────────────
# HELPER
# ─────────────────────────────────────────────────────────────────────────────

def _random_pick(options: list, count: int) -> list[int]:
    """Pick `count` random unique indices from the options list."""
    count = max(1, min(count, len(options)))
    return random.sample(list(range(len(options))), count)


# ─────────────────────────────────────────────────────────────────────────────
# HANDLERS — v1: all random
# Signature: (obs, options, min_count, max_count) -> list[int]
# Replace _random_pick with scoring logic in v2.
# ─────────────────────────────────────────────────────────────────────────────

def handle_attack(obs, options, min_count, max_count) -> list[int]:
    """
    v1: Random attack.

    v2 TODO:
        - NEVER randomly pass — if an attack is available, take it
        - Score attacks by damage vs opponent active HP remaining
        - Prefer attacks that KO this turn (damage >= hp - accumulated_damage)
        - Factor in special effects (status, bench damage, energy discard)
        - Use obs.current.opponent.active for target info
        - Use obs.current.me.active for our attacker's energy state
    """
    if obs.current:
        opp = obs.current.opponent
        if opp and opp.active:
            hp   = getattr(opp.active, 'hp', '?')
            dmg  = getattr(opp.active, 'damage', 0)
            name = getattr(opp.active, 'name', '?')
            print(f"[SelectAttack] vs {name} HP:{hp} accumulated_dmg:{dmg}")

    return _random_pick(options, min_count)


def handle_energy_attach(obs, options, min_count, max_count) -> list[int]:
    """
    v1: Random energy attachment.

    v2 TODO:
        - Attach to active first if it needs 1 more energy to attack
        - Then bench Pokémon building toward their attack cost
        - Track energy requirements per card from EN_Card_Data.csv
        - Special energy (Enriching Energy ID:13) has extra rules
    """
    return _random_pick(options, min_count)


def handle_supporter(obs, options, min_count, max_count) -> list[int]:
    """
    v1: Random Supporter.

    v2 TODO:
        - Play draw supporters (Iono, Professor's Research) when hand < 4
        - Play search supporters when you need a specific Pokémon
        - Only one Supporter per turn — choose the highest-value one
        - Don't play Iono when opponent has few prizes (helps them)
    """
    return _random_pick(options, min_count)


def handle_item(obs, options, min_count, max_count) -> list[int]:
    """
    v1: Random Item.

    v2 TODO:
        - Poké Ball variants when bench needs Pokémon
        - Evolution items when evolution target is in hand
        - Healing items when active is within KO range
        - Items can stack per turn — order matters
    """
    return _random_pick(options, min_count)


def handle_stadium(obs, options, min_count, max_count) -> list[int]:
    """
    v1: Random Stadium.

    v2 TODO:
        - Replace opponent's beneficial stadium with ours
        - Only play if it benefits our current strategy
    """
    return _random_pick(options, min_count)


def handle_retreat(obs, options, min_count, max_count) -> list[int]:
    """
    v1: Random retreat.

    v2 TODO:
        - Don't retreat if active can KO opponent this turn
        - Retreat if active is about to be KO'd AND a better attacker is benched
        - Check retreat cost vs available attached energy
        - Prefer switching to Pokémon with energy already attached
    """
    return _random_pick(options, min_count)


def handle_bench(obs, options, min_count, max_count) -> list[int]:
    """
    v1: Random bench placement.

    v2 TODO:
        - Prioritize Pokémon in the main attack line
        - Bench basics needed for evolution targets
        - Fill bench to 5 when possible
        - Avoid benching weak basics that hand opponent easy prizes
    """
    return _random_pick(options, min_count)


def handle_active(obs, options, min_count, max_count) -> list[int]:
    """
    v1: Random active selection (after a KO).

    v2 TODO: HIGH PRIORITY — second only to handle_attack
        - Best type matchup vs opponent's active
        - Prefer Pokémon with energy already attached (attack immediately)
        - Avoid sending up weak basics that give easy prizes
        - Consider prize race — are we ahead or behind?
        - Use obs.current.opponent.active for matchup info
    """
    print(f"[SelectActive] Choosing replacement after KO")
    return _random_pick(options, min_count)


def handle_prize(obs, options, min_count, max_count) -> list[int]:
    """
    v1: Random prize selection.

    v2 TODO:
        - If prizes are revealed (via effects), pick highest-value card
        - Prefer energy cards when running low
        - Prefer key Pokémon if missing from hand/bench
    """
    return _random_pick(options, min_count)


def handle_evolution(obs, options, min_count, max_count) -> list[int]:
    """
    v1: Random evolution.

    v2 TODO:
        - Always evolve if it completes the main attack line
        - Evolve active first, then bench
        - Don't evolve if it would remove useful damage counters
    """
    return _random_pick(options, min_count)


def handle_yes_no(obs, options, min_count, max_count) -> list[int]:
    """
    v1: Random yes/no.

    v2 TODO:
        - Context-specific logic per card/ability
        - Coin flip abilities: yes if upside outweighs risk
        - Discard abilities: evaluate hand quality first
    """
    return _random_pick(options, min_count)


def handle_card(obs, options, min_count, max_count) -> list[int]:
    """
    v1: Random card selection (generic search effects).

    v2 TODO:
        - Identify what the search is looking for
        - Prioritize missing combo pieces
        - Match to current hand and board needs
    """
    return _random_pick(options, min_count)


def handle_order(obs, options, min_count, max_count) -> list[int]:
    """
    v1: Random card ordering (e.g. putting cards back on deck).

    v2 TODO:
        - Put high-priority cards on top if given the choice
        - Put cards not needed soon on bottom
    """
    return _random_pick(options, min_count)


def handle_generic(obs, options, min_count, max_count) -> list[int]:
    """Catch-all for any unrecognized context — logs it so we can add a handler."""
    context = getattr(obs.select, 'context', 'UNKNOWN')
    print(f"[UNHANDLED CONTEXT: {context}] — falling back to random pick")
    return _random_pick(options, min_count)
