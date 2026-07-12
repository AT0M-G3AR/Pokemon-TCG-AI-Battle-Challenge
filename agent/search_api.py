"""
PTCG AI Battle Challenge — Search API Module
AT0M-G3AR | Gary & Team | 2026

PURPOSE:
    Implements lookahead using the official cabt Search API.
    Instead of estimating Powerful Hand damage, we CALCULATE it exactly
    by simulating the attack before committing.

    This is the "super soldier serum" — it transforms the agent from
    "I think I can KO this" to "I calculated I can KO this."

HOW THE SEARCH API WORKS:
    1. search_begin(obs) — initialize a search from current game state
       Returns a searchId
    2. search_step(searchId, [option_index]) — advance simulation one step
       Returns the next game state after making that choice
    3. Repeat search_step for each decision in the simulated future
    4. Read the resulting board state to evaluate the outcome
    5. search_end() — clean up when done

KEY INSIGHT FOR ALAKAZAM:
    Powerful Hand damage = hand_size * 20
    But hand_size CHANGES as we play cards during our turn.
    The Search API lets us simulate the full turn sequence and see
    exactly how much damage we deal after all our card plays.

USAGE IN policy.py:
    From handle_main, before scoring ATTACK options:
    1. Build the simulated turn (play cards, draw with Dudunsparce)
    2. Use search_step to simulate each action
    3. Read final hand size from the resulting state
    4. Calculate EXACT damage, not estimated damage
    5. Use that to decide whether to attack or draw more first
"""

import json
from cg.api import to_observation_class
from cg.sim import lib
import ctypes


# ─────────────────────────────────────────────────────────────────────────────
# SEARCH API WRAPPER
# ─────────────────────────────────────────────────────────────────────────────

def get_search_input(obs) -> str:
    """
    Get the search_begin_input from the observation.
    This is provided directly in obs.search_begin_input.
    It encodes the current game state for search initialization.
    """
    return getattr(obs, "search_begin_input", "")


def simulate_attack_damage(obs, attack_option_index: int) -> int:
    """
    Use the Search API to simulate what happens when we attack.
    Returns the actual damage Powerful Hand will deal.

    Args:
        obs: Current observation object
        attack_option_index: Index of the attack option to evaluate

    Returns:
        int: Exact damage that Powerful Hand will deal (hand_size * 20)
             Returns -1 if search fails
    """
    search_input = get_search_input(obs)
    if not search_input:
        return -1

    try:
        # Initialize search from current state
        search_input_bytes = search_input.encode('ascii')
        search_data = lib.SearchBegin(search_input_bytes)

        if not search_data:
            return -1

        # Parse search result
        search_json = json.loads(search_data.decode())
        search_id = search_json.get("searchId")

        if search_id is None:
            return -1

        # Step: simulate choosing the attack option
        action_array = (ctypes.c_int * 1)(attack_option_index)
        result_data = lib.SearchStep(search_id, action_array, 1)

        if not result_data:
            lib.SearchEnd()
            return -1

        result_json = json.loads(result_data.decode())

        # Read the resulting board state
        # After attack, check what hand size was at time of Powerful Hand
        current = result_json.get("current", {})
        your_index = current.get("yourIndex", 0)
        players = current.get("players", [{}, {}])

        if your_index < len(players):
            hand = players[your_index].get("hand", [])
            hand_size = len(hand)
            damage = hand_size * 20
        else:
            damage = -1

        # Clean up search
        lib.SearchEnd()
        return damage

    except Exception as e:
        print(f"[Search API] Error: {e}")
        try:
            lib.SearchEnd()
        except:
            pass
        return -1


def can_ko_with_powerful_hand(obs,
                               attack_option_index: int,
                               opponent_hp: int) -> tuple[bool, int]:
    """
    Use Search API to determine if Powerful Hand can KO the opponent.

    Returns:
        (can_ko: bool, exact_damage: int)
        If search fails, falls back to hand_size * 20 estimate
    """
    exact_damage = simulate_attack_damage(obs, attack_option_index)

    if exact_damage == -1:
        # Fallback: estimate from current hand size
        if obs.current:
            my_idx = obs.current.yourIndex
            hand_size = len(obs.current.players[my_idx].hand)
            exact_damage = hand_size * 20

    can_ko = exact_damage >= opponent_hp
    return can_ko, exact_damage


# ─────────────────────────────────────────────────────────────────────────────
# SIMPLE DAMAGE CALCULATOR (no Search API — pure math)
# Use this as fallback when Search API is unavailable
# ─────────────────────────────────────────────────────────────────────────────

def calculate_powerful_hand_damage(hand_size: int) -> int:
    """
    Powerful Hand: place 2 damage counters per card in hand.
    Each damage counter = 10 damage.
    Therefore: hand_size * 20 = total damage.
    """
    return hand_size * 20


def cards_needed_to_ko(opponent_hp: int, current_hand_size: int) -> int:
    """
    How many more cards do we need in hand to KO this target?
    Returns 0 if already lethal, positive number if we need more draws.
    """
    current_damage = calculate_powerful_hand_damage(current_hand_size)
    if current_damage >= opponent_hp:
        return 0
    damage_needed = opponent_hp - current_damage
    # Each extra card adds 20 damage
    return (damage_needed + 19) // 20  # ceiling division


def should_draw_before_attack(hand_size: int,
                               opponent_hp: int,
                               dudunsparce_on_bench: bool,
                               deck_count: int) -> bool:
    """
    Should we use Dudunsparce to draw before attacking?

    Logic:
    - If already lethal → NO (stop playing cards, attack now)
    - If drawing 3 would make us lethal AND deck is safe → YES
    - If drawing 3 still won't KO → maybe, but don't waste time

    Args:
        hand_size: Current hand size
        opponent_hp: Opponent active Pokemon's remaining HP
        dudunsparce_on_bench: Whether Dudunsparce is available to draw
        deck_count: Cards remaining in deck

    Returns:
        bool: True if we should draw first, False if we should attack now
    """
    if not dudunsparce_on_bench:
        return False

    if deck_count <= 4:
        return False  # Don't risk deck-out

    current_damage = calculate_powerful_hand_damage(hand_size)
    if current_damage >= opponent_hp:
        return False  # Already lethal — attack now

    # Simulate drawing 3 from Dudunsparce
    # Note: Dudunsparce shuffles itself back, so hand size after =
    # current_hand - 0 (Dudunsparce stays as a draw trigger) + 3 drawn
    # BUT Dudunsparce shuffles itself back INTO deck, so hand stays same
    # and we draw 3 new cards
    projected_hand = hand_size + 3
    projected_damage = calculate_powerful_hand_damage(projected_hand)

    if projected_damage >= opponent_hp:
        return True  # Drawing will give us the KO

    return False  # Drawing won't be enough either — attack anyway for pressure


# ─────────────────────────────────────────────────────────────────────────────
# ATTACK EVALUATOR — main function to call from policy.py
# ─────────────────────────────────────────────────────────────────────────────

def evaluate_attack(obs,
                    attack_index: int,
                    opponent_hp: int,
                    hand_size: int,
                    my_prizes_left: int,
                    opponent_prizes_left: int) -> float:
    """
    Score how good it is to use this attack right now.
    Uses math-based calculation (Search API as enhancement).

    Returns a score for use in handle_main's scoring array.
    Higher = better choice.
    """
    current_damage = calculate_powerful_hand_damage(hand_size)

    # TIER 1: Game-winning KO
    if current_damage >= opponent_hp and my_prizes_left <= opponent_prizes_left:
        return 20000.0  # Attack for the win

    # TIER 2: Regular KO
    if current_damage >= opponent_hp:
        return 18000.0  # Attack for a KO

    # TIER 3: Deal significant damage (>= 50% of opponent HP)
    if current_damage >= opponent_hp * 0.5:
        return 10000.0  # Deal meaningful damage

    # TIER 4: Deal some damage
    if current_damage >= 80:  # At least 80 damage
        return 6000.0

    # TIER 5: Weak attack — consider drawing first
    return 3000.0
