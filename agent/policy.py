"""
PTCG AI Battle Challenge — v2 Heuristic Policy
AT0M-G3AR | Gary & Team | 2026

DECK: Dragapult ex / Blaziken ex
WIN CONDITION: Phantom Dive (200 + 50 to 2 bench) every turn

ARCHITECTURE:
    select_action(obs) routes by SelectContext to the correct handler.
    Each handler scores every legal option and returns the best choice(s).
    Scoring is deterministic — no randomness in v2.

CARD ID CONSTANTS (this deck only):
    Pokémon:  Dreepy=119, Drakloak=120, Dragapult_ex=121
              Torchic=324, Combusken=325, Blaziken_ex=326
    Trainers: Buddy_Buddy_Poffin=1086, Night_Stretcher=1097
              Poke_Pad=1152, Rare_Candy=1079, Switch=1123
              Ultra_Ball=1121, Unfair_Stamp=1080, Risky_Ruins=1260
              Watchtower=1256, Boss_Orders=1182, Colress=1194
              Crispin=1198, Dawn=1231, Lillie=1227
    Energy:   Psychic=5, Fire=2
"""

import random
from collections import defaultdict
from cg.api import (
    Observation, SelectContext, OptionType, AreaType,
    CardType, EnergyType, Card, Pokemon, all_card_data, to_observation_class
)

# ─────────────────────────────────────────────────────────────────────────────
# CARD DATABASE — built once at import time
# ─────────────────────────────────────────────────────────────────────────────

_all_cards = all_card_data()
CARD_DB = {c.cardId: c for c in _all_cards}

# ─────────────────────────────────────────────────────────────────────────────
# DECK CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────

# Pokémon
DREEPY        = 119
DRAKLOAK      = 120
DRAGAPULT_EX  = 121
TORCHIC       = 324
COMBUSKEN     = 325
BLAZIKEN_EX   = 326

# Trainers
BUDDY_POFFIN  = 1086
NIGHT_STRETCH = 1097
POKE_PAD      = 1152
RARE_CANDY    = 1079
SWITCH        = 1123
ULTRA_BALL    = 1121
UNFAIR_STAMP  = 1080
RISKY_RUINS   = 1260
WATCHTOWER    = 1256
BOSS_ORDERS   = 1182
COLRESS       = 1194
CRISPIN       = 1198
DAWN          = 1231
LILLIE        = 1227

# Energy
PSYCHIC_ENERGY = 5
FIRE_ENERGY    = 2

# Dragapult evolution line
DRAGAPULT_LINE = {DREEPY, DRAKLOAK, DRAGAPULT_EX}
BLAZIKEN_LINE  = {TORCHIC, COMBUSKEN, BLAZIKEN_EX}

# ─────────────────────────────────────────────────────────────────────────────
# TURN STATE — reset each turn in MAIN context
# ─────────────────────────────────────────────────────────────────────────────

class TurnPlan:
    """Computed once per turn in MAIN context. Shared across all handlers."""
    should_attack: bool = False
    best_attack_index: int = 0       # index into select.option for attack
    bench_target_1: int = -1         # bench index for first damage counter
    bench_target_2: int = -1         # bench index for second damage counter
    should_retreat: bool = False
    retreat_to: int = -1             # bench index to switch into active
    boss_target: int = -1            # opponent bench index to Boss into active

_plan = TurnPlan()
_prev_turn = -1


def _reset_plan():
    global _plan
    _plan = TurnPlan()


# ─────────────────────────────────────────────────────────────────────────────
# HELPER FUNCTIONS
# ─────────────────────────────────────────────────────────────────────────────

def _safe_fallback(options: list, min_count: int) -> list[int]:
    """Last-resort random pick — should never be reached in normal play."""
    count = max(1, min(min_count, len(options)))
    return random.sample(list(range(len(options))), count)


def _pick_best(scores: list[float], min_count: int, max_count: int) -> list[int]:
    """Return indices of top-scored options, descending."""
    indexed = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)
    # Filter out options scored below -9000 (explicitly rejected)
    valid = [i for i, s in indexed if s > -9000]
    count = max(min_count, 1)
    count = min(count, len(valid), max_count)
    return [i for i, _ in indexed[:count]]


def _prize_count(pokemon: Pokemon) -> int:
    """How many prizes does KOing this Pokémon give?"""
    data = CARD_DB.get(pokemon.id)
    if not data:
        return 1
    count = 3 if getattr(data, 'megaEx', False) else 2 if getattr(data, 'ex', False) else 1
    return max(0, count)


def _hp_remaining(pokemon: Pokemon) -> int:
    """Current HP remaining on a Pokémon."""
    return max(0, pokemon.hp - getattr(pokemon, 'damage', 0))


def _energy_count(pokemon: Pokemon) -> int:
    """Total energy attached to a Pokémon."""
    return len(getattr(pokemon, 'energies', []))


def _has_energy_type(pokemon: Pokemon, energy_type: int) -> bool:
    """Check if a Pokémon has at least one of a specific energy type."""
    return energy_type in getattr(pokemon, 'energies', [])


def _bench_pokemon(state, player_index: int) -> list:
    """Return non-None bench Pokémon for a player."""
    return [p for p in state.players[player_index].bench if p is not None]


def _get_card(obs: Observation, area: AreaType, index: int, player_index: int):
    """Safely retrieve a card from any zone."""
    ps = obs.current.players[player_index]
    try:
        match area:
            case AreaType.HAND:    return ps.hand[index]
            case AreaType.BENCH:   return ps.bench[index]
            case AreaType.ACTIVE:  return ps.active[index]
            case AreaType.DISCARD: return ps.discard[index]
            case AreaType.PRIZE:   return ps.prize[index]
            case AreaType.STADIUM: return obs.current.stadium[index]
            case _:                return None
    except (IndexError, AttributeError):
        return None


def _target_score(pokemon: Pokemon, my_prizes_left: int) -> float:
    """
    Score how valuable it is to KO or damage this opponent Pokémon.
    Higher = better target.
    """
    if pokemon is None:
        return -9999
    prizes = _prize_count(pokemon)
    hp_left = _hp_remaining(pokemon)
    score = prizes * 1000          # prize value is king
    score += _energy_count(pokemon) * 150  # energy = tempo loss for opponent
    score -= hp_left * 0.5         # lower HP = closer to KO = better target
    # If we can win the game by KOing this, massive bonus
    if prizes >= my_prizes_left:
        score += 50000
    return score


def _dragapult_ready(pokemon: Pokemon) -> bool:
    """Can Dragapult ex use Phantom Dive? Needs 2 Psychic energy."""
    if pokemon.id != DRAGAPULT_EX:
        return False
    psychic_count = sum(1 for e in getattr(pokemon, 'energies', [])
                       if e == EnergyType.PSYCHIC)
    return psychic_count >= 2


def _blaziken_ready(pokemon: Pokemon) -> bool:
    """Can Blaziken ex use its attack? Needs 3 Fire energy."""
    if pokemon.id != BLAZIKEN_EX:
        return False
    fire_count = sum(1 for e in getattr(pokemon, 'energies', [])
                    if e == EnergyType.FIRE)
    return fire_count >= 3


# ─────────────────────────────────────────────────────────────────────────────
# MAIN ROUTER
# ─────────────────────────────────────────────────────────────────────────────

def select_action(obs: Observation) -> list[int]:
    """
    Routes every decision to the correct handler.
    Called by main.py on every game step.
    """
    global _prev_turn

    context   = obs.select.context
    options   = obs.select.option
    min_count = obs.select.minCount
    max_count = obs.select.maxCount

    if not options:
        return []

    # Reset turn plan at the start of each new turn
    if obs.current and obs.current.turn != _prev_turn:
        _prev_turn = obs.current.turn
        _reset_plan()

    try:
        handlers = {
            SelectContext.MAIN:                handle_main,
            SelectContext.SETUP_ACTIVE_POKEMON: handle_setup_active,
            SelectContext.SETUP_BENCH_POKEMON:  handle_setup_bench,
            SelectContext.SWITCH:               handle_switch,
            SelectContext.TO_ACTIVE:            handle_to_active,
            SelectContext.ATTACH_FROM:          handle_attach_from,
            SelectContext.TO_HAND:              handle_to_hand,
            SelectContext.DAMAGE_COUNTER:       handle_damage_counter,
            SelectContext.DAMAGE_COUNTER_ANY:   handle_damage_counter,
        }
        handler = handlers.get(context, handle_generic)
        return handler(obs, options, min_count, max_count)
    except Exception as e:
        print(f"[policy error] context={context} error={e}")
        return _safe_fallback(options, min_count)


# ─────────────────────────────────────────────────────────────────────────────
# HANDLER: MAIN — the most important decision each turn
# Scores every legal action and executes the best plan
# ─────────────────────────────────────────────────────────────────────────────

def handle_main(obs: Observation, options, min_count: int, max_count: int) -> list[int]:
    """
    MAIN context — score every legal action this turn.

    Priority order (highest score wins):
    1. Abilities (Blaziken ex energy acceleration)
    2. Evolve (Dreepy→Drakloak or Dreepy→Dragapult ex with Rare Candy)
    3. Attach energy (Psychic to Dragapult line, Fire to Blaziken line)
    4. Play Pokémon to bench (fill bench with evolution targets)
    5. Play Trainers (draw → search → disruption → switch)
    6. Attack (Phantom Dive when ready, else best available)
    7. Retreat (only when active is bad matchup)
    8. End turn (last resort)
    """
    state    = obs.current
    my_idx   = state.yourIndex
    op_idx   = 1 - my_idx
    my_state = state.players[my_idx]
    op_state = state.players[op_idx]
    my_prizes = len(my_state.prize)

    # Build hand/field/discard counts for decision making
    hand_counts    = defaultdict(int)
    field_counts   = defaultdict(int)
    discard_counts = defaultdict(int)

    for card in my_state.hand:
        hand_counts[card.id] += 1

    active = my_state.active[0] if my_state.active else None
    if active:
        field_counts[active.id] += 1

    for poke in my_state.bench:
        if poke:
            field_counts[poke.id] += 1

    for card in my_state.discard:
        discard_counts[card.id] += 1

    # Check what's available
    can_attack    = any(o.type == OptionType.ATTACK for o in options)
    can_retreat   = any(o.type == OptionType.RETREAT for o in options)
    supporter_played = getattr(state, 'supporterPlayed', False)
    energy_attached  = getattr(state, 'energyAttached', False)

    # Opponent field for targeting
    op_active = op_state.active[0] if op_state.active else None
    op_bench  = [p for p in op_state.bench if p is not None]

    scores = []
    for o in options:
        score = 0.0

        # ── ATTACK ──────────────────────────────────────────────────────────
        if o.type == OptionType.ATTACK:
            if active and _dragapult_ready(active):
                # Phantom Dive — always take it when ready
                score = 9000.0
                _plan.should_attack = True
                _plan.best_attack_index = len(scores)
            elif active and active.id == BLAZIKEN_EX and _blaziken_ready(active):
                score = 7000.0
                _plan.should_attack = True
            elif active:
                # Any other attack — score by damage potential
                score = 2000.0
            else:
                score = 500.0

        # ── ABILITY ─────────────────────────────────────────────────────────
        elif o.type == OptionType.ABILITY:
            # Blaziken ex ability — attach 2 Fire energy from discard
            # Always use if Fire energy in discard
            if discard_counts[FIRE_ENERGY] >= 1:
                score = 8500.0
            else:
                score = -9999.0  # No Fire in discard = useless

        # ── EVOLVE ──────────────────────────────────────────────────────────
        elif o.type == OptionType.EVOLVE:
            card = _get_card(obs, AreaType.HAND, o.index, my_idx)
            if card:
                if card.id == DRAGAPULT_EX:
                    score = 8000.0  # Highest priority evolution
                elif card.id == DRAKLOAK:
                    score = 6000.0
                elif card.id == BLAZIKEN_EX:
                    score = 7500.0  # Get Blaziken ability online ASAP
                elif card.id == COMBUSKEN:
                    score = 5000.0
                else:
                    score = 4000.0

        # ── PLAY CARD ────────────────────────────────────────────────────────
        elif o.type == OptionType.PLAY:
            card = _get_card(obs, AreaType.HAND, o.index, my_idx)
            if not card:
                score = 0.0
            else:
                data = CARD_DB.get(card.id)
                card_type = getattr(data, 'cardType', None)

                # Pokémon to bench
                if data and card_type == CardType.POKEMON:
                    if card.id == DREEPY:
                        bench_dreepy = field_counts[DREEPY] + field_counts[DRAKLOAK] + field_counts[DRAGAPULT_EX]
                        score = 5500.0 if bench_dreepy < 3 else 1000.0
                    elif card.id == TORCHIC:
                        score = 5000.0 if field_counts[TORCHIC] + field_counts[COMBUSKEN] + field_counts[BLAZIKEN_EX] < 2 else -9999.0
                    else:
                        score = 3000.0

                # Trainer cards
                elif data and card_type in (CardType.SUPPORTER, CardType.ITEM, CardType.STADIUM):

                    if card.id == LILLIE:
                        # Draw 4 — play when hand is small or no supporter yet
                        hand_size = len(my_state.hand)
                        if not supporter_played:
                            score = 7000.0 if hand_size <= 4 else 4000.0
                        else:
                            score = -9999.0  # Already played supporter

                    elif card.id == COLRESS:
                        # Draw until 6 — good when hand is small
                        hand_size = len(my_state.hand)
                        if not supporter_played:
                            score = 6500.0 if hand_size <= 3 else 3000.0
                        else:
                            score = -9999.0

                    elif card.id == BOSS_ORDERS:
                        # Pull a high-value benched Pokémon
                        if not supporter_played and op_bench:
                            best_bench_score = max(_target_score(p, my_prizes) for p in op_bench)
                            active_score = _target_score(op_active, my_prizes) if op_active else 0
                            if best_bench_score > active_score + 500:
                                score = 6000.0
                                _plan.boss_target = max(range(len(op_bench)),
                                    key=lambda i: _target_score(op_bench[i], my_prizes))
                            else:
                                score = -9999.0
                        else:
                            score = -9999.0

                    elif card.id == CRISPIN:
                        # Attach 2 Basic energy from discard — use when energy needed
                        psychic_discard = discard_counts[PSYCHIC_ENERGY]
                        fire_discard = discard_counts[FIRE_ENERGY]
                        if not supporter_played and (psychic_discard + fire_discard) >= 2:
                            score = 5500.0
                        elif not supporter_played and (psychic_discard + fire_discard) >= 1:
                            score = 4000.0
                        else:
                            score = -9999.0

                    elif card.id == DAWN:
                        # Move energy from bench to active
                        # Good when active Dragapult needs energy and bench has it
                        if active and active.id == DRAGAPULT_EX:
                            active_psychic = sum(1 for e in getattr(active, 'energies', [])
                                               if e == EnergyType.PSYCHIC)
                            if active_psychic < 2:
                                score = 5000.0
                            else:
                                score = 1000.0
                        else:
                            score = 2000.0

                    elif card.id == ULTRA_BALL:
                        # Discard 2, search any Pokémon
                        # High value early game to find Dreepy/Torchic
                        dreepy_needed = field_counts[DREEPY] + field_counts[DRAKLOAK] + field_counts[DRAGAPULT_EX] < 2
                        torchic_needed = field_counts[TORCHIC] + field_counts[COMBUSKEN] + field_counts[BLAZIKEN_EX] < 1
                        if dreepy_needed or torchic_needed:
                            score = 6000.0
                        else:
                            score = 2000.0

                    elif card.id == BUDDY_POFFIN:
                        # Search 2 Basic Pokémon with 70 HP or less
                        # Great early to bench Dreepy + Torchic simultaneously
                        bench_space = 5 - sum(1 for p in my_state.bench if p is not None)
                        if bench_space >= 1 and (field_counts[DREEPY] < 2 or field_counts[TORCHIC] < 1):
                            score = 6500.0
                        elif bench_space >= 1:
                            score = 2000.0
                        else:
                            score = -9999.0  # Bench full

                    elif card.id == POKE_PAD:
                        # Search Pokémon without Rule Box (finds Dreepy, Torchic, Combusken)
                        if field_counts[DREEPY] < 3 or field_counts[TORCHIC] < 2:
                            score = 5000.0
                        else:
                            score = 1500.0

                    elif card.id == RARE_CANDY:
                        # Only useful if Dreepy is in play and Dragapult ex is in hand
                        dreepy_in_play = field_counts[DREEPY] > 0
                        dragapult_in_hand = hand_counts[DRAGAPULT_EX] > 0
                        if dreepy_in_play and dragapult_in_hand:
                            score = 7500.0  # Instant Stage 2 — huge tempo
                        else:
                            score = -9999.0

                    elif card.id == SWITCH:
                        # Switch active with bench
                        # Good when active can't attack and bench attacker is ready
                        if active and active.id == DRAGAPULT_EX and _dragapult_ready(active):
                            score = -9999.0  # Don't switch away a ready Dragapult
                        elif _plan.retreat_to >= 0:
                            score = 4000.0
                        else:
                            score = 500.0

                    elif card.id == NIGHT_STRETCH:
                        # Recover 1 Pokémon + attached energy from discard
                        dragapult_discard = discard_counts[DRAGAPULT_EX]
                        dreepy_discard = discard_counts[DREEPY]
                        if dragapult_discard >= 1:
                            score = 5000.0
                        elif dreepy_discard >= 1:
                            score = 3000.0
                        else:
                            score = 500.0

                    elif card.id == UNFAIR_STAMP:
                        # Opponent shuffles hand to 2 cards
                        # Best when opponent has many prizes taken (large hand)
                        op_prizes = len(op_state.prize)
                        op_hand_size = getattr(op_state, 'handCount', 5)
                        if op_hand_size >= 6 and op_prizes <= 3:
                            score = 4500.0
                        elif op_hand_size >= 4:
                            score = 2000.0
                        else:
                            score = -9999.0

                    elif card.id == RISKY_RUINS:
                        # Stadium — each player discards energy from bench
                        score = 2000.0

                    elif card.id == WATCHTOWER:
                        # Stadium — bench damage when opponent plays basic energy
                        score = 2500.0

                    else:
                        score = 1000.0  # Unknown trainer — play it

        # ── ATTACH ENERGY ────────────────────────────────────────────────────
        elif o.type == OptionType.ATTACH:
            if not energy_attached:
                card = _get_card(obs, AreaType.HAND, o.index, my_idx)
                target = _get_card(obs, o.inPlayArea, o.inPlayIndex, my_idx)
                if card and target:
                    score = _energy_attachment_score(card, target, o.inPlayArea)
            else:
                score = -9999.0  # Already attached energy this turn

        # ── RETREAT ─────────────────────────────────────────────────────────
        elif o.type == OptionType.RETREAT:
            # Only retreat if active is about to be KO'd and can't attack well
            if active:
                hp_left = _hp_remaining(active)
                if hp_left <= 50 and active.id not in (DRAGAPULT_EX,):
                    score = 3000.0
                elif active.id == DRAGAPULT_EX and _dragapult_ready(active):
                    score = -9999.0  # Never retreat a ready Dragapult
                else:
                    score = 500.0
            else:
                score = -9999.0

        # ── END TURN ────────────────────────────────────────────────────────
        elif o.type == OptionType.END:
            score = -5000.0  # Always prefer doing something over ending

        scores.append(score)

    return _pick_best(scores, min_count, max_count)


# ─────────────────────────────────────────────────────────────────────────────
# HANDLER: DAMAGE_COUNTER — Phantom Dive bench targeting
# This is the most important handler for Dragapult ex
# ─────────────────────────────────────────────────────────────────────────────

def handle_damage_counter(obs: Observation, options, min_count: int, max_count: int) -> list[int]:
    """
    DAMAGE_COUNTER context — place 50 damage on opponent's bench targets.

    Phantom Dive places 50 damage on exactly 2 benched Pokémon.
    Strategy:
    1. Target Pokémon that will be KO'd by exactly 50 damage (free prize)
    2. Target Pokémon with most HP already damaged (closest to KO)
    3. Target Pokémon worth most prizes
    4. Prefer ex/megaEx targets over single-prize targets
    """
    state  = obs.current
    my_idx = state.yourIndex
    op_idx = 1 - my_idx
    my_prizes = len(state.players[my_idx].prize)

    scores = []
    for o in options:
        score = 0.0
        # Each option represents a bench slot to place 50 damage on
        target = None
        try:
            if o.area == AreaType.BENCH:
                target = state.players[o.playerIndex].bench[o.index]
        except (AttributeError, IndexError):
            pass

        if target is None:
            scores.append(-9999.0)
            continue

        hp_left = _hp_remaining(target)
        prizes  = _prize_count(target)

        # Will this 50 damage KO the target?
        if hp_left <= 50:
            # Free KO — massive bonus scaled by prize value
            score = 10000.0 + prizes * 2000.0
            # Game-winning KO bonus
            if prizes >= my_prizes:
                score += 50000.0
        else:
            # Score by how close to KO this gets us
            # hp_left after damage
            remaining_after = hp_left - 50
            score = prizes * 1000.0
            score += (target.hp - remaining_after) / target.hp * 500.0
            score += _energy_count(target) * 100.0

        scores.append(score)

    # Must pick exactly min_count targets (usually 2 for Phantom Dive)
    return _pick_best(scores, min_count, max_count)


# ─────────────────────────────────────────────────────────────────────────────
# HANDLER: SETUP_ACTIVE_POKEMON — choosing your starter
# ─────────────────────────────────────────────────────────────────────────────

def handle_setup_active(obs: Observation, options, min_count: int, max_count: int) -> list[int]:
    """
    Choose which Pokémon to place as Active during game setup.
    Priority: Dreepy > Torchic > anything else
    Dreepy is preferred — it's the Dragapult line and our main attacker.
    """
    scores = []
    for o in options:
        card = _get_card(obs, AreaType.HAND, o.index, obs.current.yourIndex)
        if not card:
            scores.append(0.0)
            continue
        if card.id == DREEPY:
            scores.append(100.0)
        elif card.id == TORCHIC:
            scores.append(60.0)
        elif card.id == COMBUSKEN:
            scores.append(40.0)
        else:
            scores.append(10.0)
    return _pick_best(scores, min_count, max_count)


# ─────────────────────────────────────────────────────────────────────────────
# HANDLER: SETUP_BENCH_POKEMON — filling bench during setup
# ─────────────────────────────────────────────────────────────────────────────

def handle_setup_bench(obs: Observation, options, min_count: int, max_count: int) -> list[int]:
    """
    Fill bench during setup phase.
    Priority: Dreepy (need 3 total) > Torchic (need 1-2) > others
    """
    state  = obs.current
    my_idx = state.yourIndex
    field_counts = defaultdict(int)
    for p in state.players[my_idx].bench:
        if p:
            field_counts[p.id] += 1
    active = state.players[my_idx].active[0] if state.players[my_idx].active else None
    if active:
        field_counts[active.id] += 1

    scores = []
    for o in options:
        card = _get_card(obs, AreaType.HAND, o.index, my_idx)
        if not card:
            scores.append(0.0)
            continue
        if card.id == DREEPY:
            needed = max(0, 3 - field_counts[DREEPY])
            scores.append(100.0 * needed if needed > 0 else 10.0)
        elif card.id == TORCHIC:
            needed = max(0, 2 - field_counts[TORCHIC])
            scores.append(80.0 * needed if needed > 0 else 5.0)
        else:
            scores.append(20.0)
    return _pick_best(scores, min_count, max_count)


# ─────────────────────────────────────────────────────────────────────────────
# HANDLER: SWITCH / TO_ACTIVE — choosing which Pokémon becomes Active
# ─────────────────────────────────────────────────────────────────────────────

def handle_switch(obs: Observation, options, min_count: int, max_count: int) -> list[int]:
    return handle_to_active(obs, options, min_count, max_count)


def handle_to_active(obs: Observation, options, min_count: int, max_count: int) -> list[int]:
    """
    Choose which benched Pokémon becomes Active.
    Triggered by: KO, Switch card, Retreat.

    Priority:
    1. Dragapult ex with 2+ Psychic energy (ready to attack)
    2. Dragapult ex with 1 Psychic energy (almost ready)
    3. Drakloak (building toward Dragapult)
    4. Blaziken ex (if active can accelerate energy)
    5. Dreepy (worst case — can't attack but keeps game going)
    """
    state  = obs.current
    my_idx = state.yourIndex

    scores = []
    for o in options:
        poke = _get_card(obs, AreaType.BENCH, o.index, my_idx)
        if not poke:
            scores.append(0.0)
            continue

        energy = _energy_count(poke)
        psychic = sum(1 for e in getattr(poke, 'energies', []) if e == EnergyType.PSYCHIC)
        hp_left = _hp_remaining(poke)

        if poke.id == DRAGAPULT_EX:
            if psychic >= 2:
                score = 10000.0 + energy * 100  # Ready to sweep
            elif psychic == 1:
                score = 7000.0 + energy * 50    # One energy away
            else:
                score = 4000.0
        elif poke.id == DRAKLOAK:
            score = 3000.0 + energy * 100
        elif poke.id == BLAZIKEN_EX:
            score = 3500.0 + energy * 100
        elif poke.id == DREEPY:
            score = 1000.0
        elif poke.id == TORCHIC or poke.id == COMBUSKEN:
            score = 800.0
        else:
            score = 500.0

        # Don't send up something with very low HP
        if hp_left <= 30:
            score -= 2000.0

        scores.append(score)

    return _pick_best(scores, min_count, max_count)


# ─────────────────────────────────────────────────────────────────────────────
# HANDLER: ATTACH_FROM — choosing energy to attach
# ─────────────────────────────────────────────────────────────────────────────

def handle_attach_from(obs: Observation, options, min_count: int, max_count: int) -> list[int]:
    """
    Choose which energy to attach and where.
    Psychic → Dragapult line, Fire → Blaziken line.
    """
    state  = obs.current
    my_idx = state.yourIndex

    scores = []
    for o in options:
        card = _get_card(obs, AreaType.HAND, o.index, my_idx)
        if not card:
            scores.append(0.0)
            continue
        target_poke = _get_card(obs, o.inPlayArea, o.inPlayIndex, my_idx)
        if not target_poke:
            scores.append(0.0)
            continue
        scores.append(_energy_attachment_score(card, target_poke, o.inPlayArea))

    return _pick_best(scores, min_count, max_count)


def _energy_attachment_score(energy_card, target: Pokemon, area: AreaType) -> float:
    """Score how good it is to attach this energy to this target."""
    energy_id = energy_card.id
    target_id = target.id
    current_energy = _energy_count(target)
    is_active = (area == AreaType.ACTIVE)
    score = 0.0

    if energy_id == PSYCHIC_ENERGY:
        if target_id == DRAGAPULT_EX:
            psychic_count = sum(1 for e in getattr(target, 'energies', [])
                               if e == EnergyType.PSYCHIC)
            if psychic_count < 2:
                score = 9000.0  # Completing Phantom Dive requirement
            else:
                score = 2000.0  # Extra energy is fine
        elif target_id == DRAKLOAK:
            score = 5000.0  # Pre-load for when it evolves
        elif target_id == DREEPY:
            score = 3000.0  # Early pre-loading
        else:
            score = 500.0

    elif energy_id == FIRE_ENERGY:
        if target_id == BLAZIKEN_EX:
            fire_count = sum(1 for e in getattr(target, 'energies', [])
                            if e == EnergyType.FIRE)
            if fire_count < 3:
                score = 8000.0  # Building to Blaziken attack
            else:
                score = 1000.0
        elif target_id == COMBUSKEN:
            score = 4000.0  # Pre-load for evolution
        elif target_id == TORCHIC:
            score = 2000.0
        else:
            score = 500.0

    # Active Pokémon gets small bonus — can use energy immediately
    if is_active:
        score += 200.0

    return score


# ─────────────────────────────────────────────────────────────────────────────
# HANDLER: TO_HAND — choosing cards to add to hand (search effects)
# ─────────────────────────────────────────────────────────────────────────────

def handle_to_hand(obs: Observation, options, min_count: int, max_count: int) -> list[int]:
    """
    Choose which card(s) to take into hand from search effects.
    Priority: missing evolution pieces > energy > other cards
    """
    state  = obs.current
    my_idx = state.yourIndex

    field_counts = defaultdict(int)
    hand_counts  = defaultdict(int)

    active = state.players[my_idx].active[0] if state.players[my_idx].active else None
    if active:
        field_counts[active.id] += 1
    for p in state.players[my_idx].bench:
        if p:
            field_counts[p.id] += 1
    for c in state.players[my_idx].hand:
        hand_counts[c.id] += 1

    scores = []
    for o in options:
        card = _get_card(obs, o.area, o.index, my_idx)
        if not card:
            scores.append(0.0)
            continue

        cid = card.id
        score = 100.0  # baseline

        # Evolution pieces we need
        dragapult_in_field = field_counts[DREEPY] + field_counts[DRAKLOAK] + field_counts[DRAGAPULT_EX]
        blaziken_in_field  = field_counts[TORCHIC] + field_counts[COMBUSKEN] + field_counts[BLAZIKEN_EX]

        if cid == DRAGAPULT_EX:
            score = 9000.0 if dragapult_in_field >= 1 else 3000.0
        elif cid == BLAZIKEN_EX:
            score = 8000.0 if blaziken_in_field >= 1 else 2000.0
        elif cid == RARE_CANDY:
            score = 7000.0 if field_counts[DREEPY] >= 1 else 2000.0
        elif cid == DREEPY:
            score = 5000.0 if dragapult_in_field < 3 else 1000.0
        elif cid == DRAKLOAK:
            score = 4000.0 if field_counts[DREEPY] >= 1 else 500.0
        elif cid == TORCHIC:
            score = 4500.0 if blaziken_in_field < 2 else 500.0
        elif cid == PSYCHIC_ENERGY:
            score = 3000.0
        elif cid == FIRE_ENERGY:
            score = 2500.0
        elif cid == LILLIE or cid == COLRESS:
            score = 2000.0
        elif cid == BOSS_ORDERS:
            score = 3500.0
        elif cid == DAWN:
            score = 2800.0
        elif cid == ULTRA_BALL or cid == BUDDY_POFFIN:
            score = 2200.0

        # Penalise duplicates already in hand
        score -= hand_counts[cid] * 500.0

        scores.append(score)

    return _pick_best(scores, min_count, max_count)


# ─────────────────────────────────────────────────────────────────────────────
# HANDLER: GENERIC — catch-all for unhandled contexts
# ─────────────────────────────────────────────────────────────────────────────

def handle_generic(obs: Observation, options, min_count: int, max_count: int) -> list[int]:
    """Catch-all. Logs the unknown context and picks randomly."""
    context = getattr(obs.select, 'context', 'UNKNOWN')
    print(f"[UNHANDLED CONTEXT: {context}] — using random pick")
    return _safe_fallback(options, min_count)
