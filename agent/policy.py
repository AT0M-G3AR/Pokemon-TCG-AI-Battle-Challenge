"""
PTCG AI Battle Challenge — v2.1 Heuristic Policy
AT0M-G3AR | Gary & Team | 2026

DECK: Dragapult ex / Blaziken ex
WIN CONDITION: Phantom Dive (1 Psychic + 1 Fire → 200 active + 60 spread to bench)

FIXES FROM v2.0:
  - Context integers corrected from SelectContext enum lookup
  - ATTACH_TO (22) now handled — energy goes to correct Pokémon
  - TO_BENCH (5) now handled — bench placement is intentional
  - DISCARD (8) now handled — Ultra Ball discards correctly chosen
  - DISCARD_ENERGY (30) now handled
  - EVOLVE (37) now handled
  - Dragapult ex attack cost corrected: 1 Psychic + 1 Fire (not 2 Psychic)
  - DAMAGE_COUNTER: distribute 60 total damage across bench targets
  - Dawn: corrected to search Basic + Stage1 + Stage2 into hand
  - Crispin: corrected to search 2 energy from deck (not discard)
  - Lillie's Determination: draw 6 (or 8 with 6 prizes) — play on bad/small hand
  - Colress's Tenacity: searches Stadium + Energy into hand

CARD ID CONSTANTS:
    Pokémon:  Dreepy=119, Drakloak=120, Dragapult_ex=121
              Torchic=324, Combusken=325, Blaziken_ex=326
    Trainers: Buddy_Poffin=1086, Night_Stretcher=1097
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
DREEPY        = 119
DRAKLOAK      = 120
DRAGAPULT_EX  = 121
TORCHIC       = 324
COMBUSKEN     = 325
BLAZIKEN_EX   = 326

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

PSYCHIC_ENERGY = 5
FIRE_ENERGY    = 2

DRAGAPULT_LINE = {DREEPY, DRAKLOAK, DRAGAPULT_EX}
BLAZIKEN_LINE  = {TORCHIC, COMBUSKEN, BLAZIKEN_EX}

# ─────────────────────────────────────────────────────────────────────────────
# CONTEXT INTEGER MAP — verified from SelectContext enum
# ─────────────────────────────────────────────────────────────────────────────
CTX_MAIN              = SelectContext.MAIN
CTX_SETUP_ACTIVE      = SelectContext.SETUP_ACTIVE_POKEMON
CTX_SETUP_BENCH       = SelectContext.SETUP_BENCH_POKEMON   # value=2
CTX_TO_BENCH          = SelectContext.TO_BENCH               # value=5
CTX_TO_HAND           = SelectContext.TO_HAND                # value=7
CTX_DISCARD           = SelectContext.DISCARD                # value=8
CTX_SWITCH            = SelectContext.SWITCH
CTX_TO_ACTIVE         = SelectContext.TO_ACTIVE
CTX_ATTACH_FROM       = SelectContext.ATTACH_FROM            # value=21
CTX_ATTACH_TO         = SelectContext.ATTACH_TO              # value=22
CTX_DISCARD_ENERGY    = SelectContext.DISCARD_ENERGY         # value=30
CTX_EVOLVE            = SelectContext.EVOLVE                 # value=37
CTX_DAMAGE_COUNTER    = SelectContext.DAMAGE_COUNTER
CTX_DAMAGE_CTR_ANY    = SelectContext.DAMAGE_COUNTER_ANY

# ─────────────────────────────────────────────────────────────────────────────
# TURN STATE
# ─────────────────────────────────────────────────────────────────────────────
_prev_turn = -1
_last_attach_card_id = PSYCHIC_ENERGY  # tracks which energy we picked in ATTACH_FROM


def _safe_fallback(options: list, min_count: int) -> list[int]:
    count = max(1, min(min_count, len(options)))
    return random.sample(list(range(len(options))), count)


def _pick_best(scores: list, min_count: int, max_count: int) -> list[int]:
    indexed = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)
    valid = [i for i, s in indexed if s > -9000]
    if not valid:
        valid = [indexed[0][0]] if indexed else [0]
    count = max(min_count, 1)
    count = min(count, len(valid), max_count)
    return [i for i, _ in indexed[:count]]


def _prize_count(pokemon: Pokemon) -> int:
    data = CARD_DB.get(pokemon.id)
    if not data:
        return 1
    return 3 if getattr(data, 'megaEx', False) else 2 if getattr(data, 'ex', False) else 1


def _hp_remaining(pokemon: Pokemon) -> int:
    return max(0, pokemon.hp - getattr(pokemon, 'damage', 0))


def _energy_count(pokemon: Pokemon) -> int:
    return len(getattr(pokemon, 'energies', []))


def _has_energy(pokemon: Pokemon, energy_type) -> bool:
    return energy_type in getattr(pokemon, 'energies', [])


def _dragapult_ready(pokemon: Pokemon) -> bool:
    """Dragapult ex needs 1 Psychic + 1 Fire for Phantom Dive."""
    if pokemon.id != DRAGAPULT_EX:
        return False
    energies = getattr(pokemon, 'energies', [])
    has_psychic = EnergyType.PSYCHIC in energies
    has_fire    = EnergyType.FIRE in energies
    return has_psychic and has_fire


def _dragapult_one_away(pokemon: Pokemon) -> bool:
    """Dragapult has 1 of the 2 required energy types."""
    if pokemon.id != DRAGAPULT_EX:
        return False
    energies = getattr(pokemon, 'energies', [])
    has_psychic = EnergyType.PSYCHIC in energies
    has_fire    = EnergyType.FIRE in energies
    return has_psychic or has_fire


def _get_card(obs: Observation, area, index: int, player_index: int):
    ps = obs.current.players[player_index]
    try:
        match area:
            case AreaType.HAND:    return ps.hand[index]
            case AreaType.BENCH:   return ps.bench[index]
            case AreaType.ACTIVE:  return ps.active[index]
            case AreaType.DISCARD: return ps.discard[index]
            case AreaType.PRIZE:   return ps.prize[index]
            case _:                return None
    except (IndexError, AttributeError):
        return None


def _field_counts(state, player_index: int) -> dict:
    counts = defaultdict(int)
    active = state.players[player_index].active
    if active and active[0]:
        counts[active[0].id] += 1
    for p in state.players[player_index].bench:
        if p:
            counts[p.id] += 1
    return counts


def _hand_counts(state, player_index: int) -> dict:
    counts = defaultdict(int)
    for c in state.players[player_index].hand:
        counts[c.id] += 1
    return counts


def _discard_counts(state, player_index: int) -> dict:
    counts = defaultdict(int)
    for c in state.players[player_index].discard:
        counts[c.id] += 1
    return counts


def _target_score(pokemon: Pokemon, my_prizes_left: int) -> float:
    if pokemon is None:
        return -9999.0
    prizes  = _prize_count(pokemon)
    hp_left = _hp_remaining(pokemon)
    score   = prizes * 1000.0
    score  += _energy_count(pokemon) * 150.0
    score  -= hp_left * 0.3
    if prizes >= my_prizes_left:
        score += 50000.0
    return score


# ─────────────────────────────────────────────────────────────────────────────
# MAIN ROUTER
# ─────────────────────────────────────────────────────────────────────────────

def select_action(obs: Observation) -> list[int]:
    global _prev_turn

    context   = obs.select.context
    options   = obs.select.option
    min_count = obs.select.minCount
    max_count = obs.select.maxCount

    if not options:
        return []

    if obs.current and obs.current.turn != _prev_turn:
        _prev_turn = obs.current.turn

    try:
        handlers = {
            CTX_MAIN:           handle_main,
            CTX_SETUP_ACTIVE:   handle_setup_active,
            CTX_SETUP_BENCH:    handle_setup_bench,
            CTX_TO_BENCH:       handle_to_bench,
            CTX_TO_HAND:        handle_to_hand,
            CTX_DISCARD:        handle_discard,
            CTX_SWITCH:         handle_to_active,
            CTX_TO_ACTIVE:      handle_to_active,
            CTX_ATTACH_FROM:    handle_attach_from,
            CTX_ATTACH_TO:      handle_attach_to,
            CTX_DISCARD_ENERGY: handle_discard_energy,
            CTX_EVOLVE:         handle_evolve,
            CTX_DAMAGE_COUNTER: handle_damage_counter,
            CTX_DAMAGE_CTR_ANY: handle_damage_counter,
        }
        handler = handlers.get(context, handle_generic)
        return handler(obs, options, min_count, max_count)
    except Exception as e:
        print(f"[policy error] ctx={context} err={e}")
        return _safe_fallback(options, min_count)


# ─────────────────────────────────────────────────────────────────────────────
# HANDLER: MAIN
# ─────────────────────────────────────────────────────────────────────────────

def handle_main(obs: Observation, options, min_count: int, max_count: int) -> list[int]:
    state    = obs.current
    my_idx   = state.yourIndex
    op_idx   = 1 - my_idx
    my_state = state.players[my_idx]
    op_state = state.players[op_idx]
    my_prizes = len(my_state.prize)

    hand   = _hand_counts(state, my_idx)
    field  = _field_counts(state, my_idx)
    discard = _discard_counts(state, my_idx)

    supporter_played = getattr(state, 'supporterPlayed', False)
    energy_attached  = getattr(state, 'energyAttached', False)

    active = my_state.active[0] if my_state.active else None
    op_active = op_state.active[0] if op_state.active else None
    op_bench  = [p for p in op_state.bench if p is not None]

    dragapult_in_field = field[DREEPY] + field[DRAKLOAK] + field[DRAGAPULT_EX]
    blaziken_in_field  = field[TORCHIC] + field[COMBUSKEN] + field[BLAZIKEN_EX]
    bench_space = 5 - sum(1 for p in my_state.bench if p is not None)

    scores = []
    for o in options:
        score = 0.0

        # ── ATTACK ──────────────────────────────────────────────────────────
        if o.type == OptionType.ATTACK:
            if active and _dragapult_ready(active):
                score = 9000.0   # Phantom Dive — always fire when ready
            elif active and active.id == BLAZIKEN_EX:
                fire_count = sum(1 for e in getattr(active, 'energies', [])
                                if e == EnergyType.FIRE)
                score = 7000.0 if fire_count >= 3 else 3000.0
            else:
                score = 2000.0

        # ── ABILITY ─────────────────────────────────────────────────────────
        elif o.type == OptionType.ABILITY:
            # Blaziken ex: attach 2 Fire from discard to your Pokémon
            fire_in_discard = discard[FIRE_ENERGY]
            score = 8500.0 if fire_in_discard >= 1 else -9999.0

        # ── EVOLVE ──────────────────────────────────────────────────────────
        elif o.type == OptionType.EVOLVE:
            card = _get_card(obs, AreaType.HAND, o.index, my_idx)
            if card:
                if card.id == DRAGAPULT_EX:  score = 8000.0
                elif card.id == BLAZIKEN_EX: score = 7500.0
                elif card.id == DRAKLOAK:    score = 6000.0
                elif card.id == COMBUSKEN:   score = 5000.0
                else:                        score = 3000.0

        # ── PLAY CARD ────────────────────────────────────────────────────────
        elif o.type == OptionType.PLAY:
            card = _get_card(obs, AreaType.HAND, o.index, my_idx)
            if not card:
                score = 0.0
            else:
                data = CARD_DB.get(card.id)
                card_type = getattr(data, 'cardType', None)

                if data and card_type == CardType.POKEMON:
                    # Play Pokémon to bench
                    if card.id == DREEPY:
                        score = 5500.0 if dragapult_in_field < 3 and bench_space > 0 else -9999.0
                    elif card.id == TORCHIC:
                        score = 5000.0 if blaziken_in_field < 2 and bench_space > 0 else -9999.0
                    else:
                        score = 2000.0 if bench_space > 0 else -9999.0

                else:
                    # Trainer cards
                    cid = card.id

                    if cid == LILLIE:
                        # Shuffle hand, draw 6 (or 8 with 6 prizes)
                        # Best on turn 1 with 6 prizes (draw 8) or bad hand
                        hand_size = len(my_state.hand)
                        if not supporter_played:
                            if my_prizes == 6:
                                score = 8000.0   # Draw 8 — premium turn 1 play
                            elif hand_size <= 3:
                                score = 7000.0   # Bad hand — refresh
                            elif hand_size <= 5:
                                score = 5000.0
                            else:
                                score = 2000.0   # OK hand — lower priority
                        else:
                            score = -9999.0

                    elif cid == DAWN:
                        # Search Basic + Stage 1 + Stage 2 → hand
                        # Best early to assemble Dragapult line
                        missing_dreepy    = dragapult_in_field + hand[DREEPY] < 2
                        missing_drakloak  = field[DRAKLOAK] + hand[DRAKLOAK] < 1
                        missing_dragapult = field[DRAGAPULT_EX] + hand[DRAGAPULT_EX] < 1
                        if not supporter_played:
                            if missing_dreepy or missing_drakloak or missing_dragapult:
                                score = 7500.0
                            else:
                                score = 2000.0  # Have the line — lower value
                        else:
                            score = -9999.0

                    elif cid == CRISPIN:
                        # Search 2 different Basic Energy from deck
                        # Attach 1 directly, put 1 in hand
                        # Always useful — searches from deck not discard
                        if not supporter_played:
                            dragapult_active = (active and active.id == DRAGAPULT_EX)
                            if dragapult_active and not _dragapult_ready(active):
                                score = 8000.0   # Gets Dragapult both energy types
                            else:
                                score = 5500.0
                        else:
                            score = -9999.0

                    elif cid == COLRESS:
                        # Search Stadium + Energy → hand
                        stadium_in_hand = hand[RISKY_RUINS] + hand[WATCHTOWER]
                        energy_in_hand  = hand[PSYCHIC_ENERGY] + hand[FIRE_ENERGY]
                        if not supporter_played:
                            if stadium_in_hand == 0 or energy_in_hand == 0:
                                score = 6000.0   # Missing either piece
                            else:
                                score = 3000.0
                        else:
                            score = -9999.0

                    elif cid == BOSS_ORDERS:
                        # Switch opponent's benched Pokémon to active
                        if not supporter_played and op_bench:
                            best_bench = max(_target_score(p, my_prizes) for p in op_bench)
                            active_val  = _target_score(op_active, my_prizes) if op_active else 0
                            if best_bench > active_val + 300:
                                score = 6500.0
                            else:
                                score = -9999.0
                        else:
                            score = -9999.0

                    elif cid == BUDDY_POFFIN:
                        # Search 2 Basics ≤70 HP → bench (Item, no supporter limit)
                        # Finds Dreepy (70HP) + Torchic (70HP) simultaneously
                        if bench_space >= 1:
                            needs_dreepy  = dragapult_in_field < 2
                            needs_torchic = blaziken_in_field < 1
                            if needs_dreepy and needs_torchic:
                                score = 7000.0   # Gets both at once
                            elif needs_dreepy or needs_torchic:
                                score = 5500.0
                            else:
                                score = 1500.0
                        else:
                            score = -9999.0

                    elif cid == ULTRA_BALL:
                        # Discard 2 cards, search any Pokémon
                        # High value when missing key pieces
                        needs_dragapult = field[DRAGAPULT_EX] + hand[DRAGAPULT_EX] < 2
                        needs_blaziken  = field[BLAZIKEN_EX] + hand[BLAZIKEN_EX] < 1
                        needs_dreepy    = dragapult_in_field < 2
                        hand_size       = len(my_state.hand)
                        if hand_size >= 3:   # Need cards to discard
                            if needs_dragapult or needs_blaziken:
                                score = 6500.0
                            elif needs_dreepy:
                                score = 5000.0
                            else:
                                score = 2000.0
                        else:
                            score = -9999.0  # Can't afford the discard cost

                    elif cid == POKE_PAD:
                        # Search Pokémon without Rule Box → hand
                        # Finds Dreepy, Drakloak, Torchic, Combusken
                        if dragapult_in_field < 2 or blaziken_in_field < 1:
                            score = 5500.0
                        else:
                            score = 1500.0

                    elif cid == RARE_CANDY:
                        # Evolve Basic directly to Stage 2 (Dreepy → Dragapult ex)
                        dreepy_in_play    = field[DREEPY] > 0
                        dragapult_in_hand = hand[DRAGAPULT_EX] > 0
                        if dreepy_in_play and dragapult_in_hand:
                            score = 8500.0   # Massive tempo — instant Stage 2
                        else:
                            score = -9999.0

                    elif cid == SWITCH:
                        # Switch active with bench Pokémon
                        ready_on_bench = any(
                            p and _dragapult_ready(p)
                            for p in my_state.bench if p
                        )
                        if ready_on_bench and active and not _dragapult_ready(active):
                            score = 5000.0
                        elif active and _hp_remaining(active) <= 50:
                            score = 4000.0
                        else:
                            score = -9999.0

                    elif cid == NIGHT_STRETCH:
                        # Recover 1 Pokémon + attached energy from discard
                        dragapult_lost = discard[DRAGAPULT_EX]
                        dreepy_lost    = discard[DREEPY]
                        blaziken_lost  = discard[BLAZIKEN_EX]
                        if dragapult_lost >= 1:
                            score = 5500.0
                        elif blaziken_lost >= 1:
                            score = 4000.0
                        elif dreepy_lost >= 1:
                            score = 3000.0
                        else:
                            score = 500.0

                    elif cid == UNFAIR_STAMP:
                        # Opponent shuffles hand to 2 cards (only when behind)
                        op_prizes    = len(op_state.prize)
                        op_hand_size = getattr(op_state, 'handCount', 5)
                        if my_prizes > op_prizes and op_hand_size >= 5:
                            score = 5000.0  # We're behind, they have big hand
                        else:
                            score = -9999.0

                    elif cid in (RISKY_RUINS, WATCHTOWER):
                        score = 2000.0   # Stadiums — play when available

                    else:
                        score = 1000.0

        # ── ATTACH ──────────────────────────────────────────────────────────
        elif o.type == OptionType.ATTACH:
            if not energy_attached:
                card   = _get_card(obs, AreaType.HAND, o.index, my_idx)
                target = _get_card(obs, o.inPlayArea, o.inPlayIndex, my_idx)
                if card and target:
                    score = _energy_score(card.id, target)
            else:
                score = -9999.0

        # ── RETREAT ─────────────────────────────────────────────────────────
        elif o.type == OptionType.RETREAT:
            if active:
                hp = _hp_remaining(active)
                ready_on_bench = any(
                    p and _dragapult_ready(p)
                    for p in my_state.bench if p
                )
                if hp <= 50 and ready_on_bench:
                    score = 4000.0
                elif active.id == DRAGAPULT_EX and _dragapult_ready(active):
                    score = -9999.0  # Never retreat a ready Dragapult
                else:
                    score = 500.0
            else:
                score = -9999.0

        # ── END ─────────────────────────────────────────────────────────────
        elif o.type == OptionType.END:
            score = -5000.0

        scores.append(score)

    return _pick_best(scores, min_count, max_count)


# ─────────────────────────────────────────────────────────────────────────────
# ENERGY SCORING HELPER
# Dragapult ex needs 1 Psychic + 1 Fire for Phantom Dive
# ─────────────────────────────────────────────────────────────────────────────

def _energy_score(energy_id: int, target: Pokemon) -> float:
    """Score attaching this energy type to this target Pokémon."""
    tid = target.id
    energies = getattr(target, 'energies', [])
    has_psychic = EnergyType.PSYCHIC in energies
    has_fire    = EnergyType.FIRE in energies
    score = 0.0

    if energy_id == PSYCHIC_ENERGY:
        if tid == DRAGAPULT_EX:
            if not has_psychic and has_fire:
                score = 9500.0   # Completes Phantom Dive requirement!
            elif not has_psychic:
                score = 8000.0   # First Psychic on Dragapult
            else:
                score = 2000.0   # Extra psychic
        elif tid == DRAKLOAK:
            score = 5000.0       # Pre-load for evolution
        elif tid == DREEPY:
            score = 3000.0
        else:
            score = 500.0

    elif energy_id == FIRE_ENERGY:
        if tid == DRAGAPULT_EX:
            if not has_fire and has_psychic:
                score = 9500.0   # Completes Phantom Dive requirement!
            elif not has_fire:
                score = 8000.0   # First Fire on Dragapult
            else:
                score = 2000.0
        elif tid == BLAZIKEN_EX:
            fire_count = sum(1 for e in energies if e == EnergyType.FIRE)
            score = 7000.0 if fire_count < 3 else 1000.0
        elif tid == COMBUSKEN:
            score = 4000.0
        elif tid == TORCHIC:
            score = 2000.0
        else:
            score = 500.0

    return score


# ─────────────────────────────────────────────────────────────────────────────
# HANDLER: DAMAGE_COUNTER — Phantom Dive bench targeting
# Distribute 60 total damage across opponent's bench
# ─────────────────────────────────────────────────────────────────────────────

def handle_damage_counter(obs: Observation, options, min_count: int, max_count: int) -> list[int]:
    """
    Phantom Dive spreads 60 damage across bench targets.
    The agent distributes all damage to one target if it gets a KO,
    otherwise splits to put multiple targets into KO range.

    Each option = one bench slot to place damage on.
    min_count = how many targets we must pick (usually the spread amount).
    """
    state     = obs.current
    my_idx    = state.yourIndex
    op_idx    = 1 - my_idx
    my_prizes = len(state.players[my_idx].prize)

    scores = []
    for o in options:
        score = 0.0
        target = None
        try:
            if hasattr(o, 'area') and o.area == AreaType.BENCH:
                target = state.players[op_idx].bench[o.index]
        except (AttributeError, IndexError):
            pass

        if target is None:
            scores.append(-9999.0)
            continue

        hp_left = _hp_remaining(target)
        prizes  = _prize_count(target)

        # Calculate damage per counter placement
        # If min_count = 1, we concentrate all 60 on one target
        # If min_count = 2, we're splitting — estimate ~30 per target
        damage_per_placement = 60 // max(min_count, 1)

        if hp_left <= damage_per_placement:
            # This placement KOs the target — massive bonus
            score = 15000.0 + prizes * 3000.0
            if prizes >= my_prizes:
                score += 50000.0  # Game-winning KO
        elif hp_left <= 60:
            # Won't KO with this split but Phantom Dive base damage might
            score = 8000.0 + prizes * 1000.0
        else:
            # Set up future KO — score by prize value and damage progress
            score = prizes * 1000.0
            score += (1.0 - hp_left / target.hp) * 500.0
            score += _energy_count(target) * 100.0

        scores.append(score)

    return _pick_best(scores, min_count, max_count)


# ─────────────────────────────────────────────────────────────────────────────
# HANDLER: SETUP_ACTIVE_POKEMON
# ─────────────────────────────────────────────────────────────────────────────

def handle_setup_active(obs: Observation, options, min_count: int, max_count: int) -> list[int]:
    """Start with Dreepy as active — it's our main evolution line."""
    my_idx = obs.current.yourIndex
    scores = []
    for o in options:
        card = _get_card(obs, AreaType.HAND, o.index, my_idx)
        if not card:
            scores.append(0.0)
            continue
        if card.id == DREEPY:         scores.append(100.0)
        elif card.id == TORCHIC:      scores.append(60.0)
        elif card.id == COMBUSKEN:    scores.append(40.0)
        else:                         scores.append(10.0)
    return _pick_best(scores, min_count, max_count)


# ─────────────────────────────────────────────────────────────────────────────
# HANDLER: SETUP_BENCH_POKEMON (context=2)
# ─────────────────────────────────────────────────────────────────────────────

def handle_setup_bench(obs: Observation, options, min_count: int, max_count: int) -> list[int]:
    """Fill bench during setup. Priority: Dreepy x2 + Torchic x1 minimum."""
    state  = obs.current
    my_idx = state.yourIndex
    field  = _field_counts(state, my_idx)

    scores = []
    for o in options:
        card = _get_card(obs, AreaType.HAND, o.index, my_idx)
        if not card:
            scores.append(0.0)
            continue
        if card.id == DREEPY:
            needed = max(0, 3 - field[DREEPY])
            scores.append(100.0 + needed * 20)
        elif card.id == TORCHIC:
            needed = max(0, 2 - field[TORCHIC])
            scores.append(80.0 + needed * 20)
        else:
            scores.append(20.0)
    return _pick_best(scores, min_count, max_count)


# ─────────────────────────────────────────────────────────────────────────────
# HANDLER: TO_BENCH (context=5) — place a Pokémon from hand onto bench
# ─────────────────────────────────────────────────────────────────────────────

def handle_to_bench(obs: Observation, options, min_count: int, max_count: int) -> list[int]:
    """Choose which Pokémon to place onto the bench mid-game."""
    state  = obs.current
    my_idx = state.yourIndex
    field  = _field_counts(state, my_idx)
    bench_space = 5 - sum(1 for p in state.players[my_idx].bench if p is not None)

    scores = []
    for o in options:
        card = _get_card(obs, AreaType.HAND, o.index, my_idx)
        if not card or bench_space <= 0:
            scores.append(-9999.0)
            continue

        dragapult_in_field = field[DREEPY] + field[DRAKLOAK] + field[DRAGAPULT_EX]
        blaziken_in_field  = field[TORCHIC] + field[COMBUSKEN] + field[BLAZIKEN_EX]

        if card.id == DREEPY:
            scores.append(100.0 if dragapult_in_field < 3 else 10.0)
        elif card.id == TORCHIC:
            scores.append(80.0 if blaziken_in_field < 2 else 5.0)
        elif card.id == DRAKLOAK:
            scores.append(60.0 if field[DREEPY] >= 1 else 20.0)
        elif card.id == COMBUSKEN:
            scores.append(50.0 if field[TORCHIC] >= 1 else 15.0)
        else:
            scores.append(20.0)
    return _pick_best(scores, min_count, max_count)


# ─────────────────────────────────────────────────────────────────────────────
# HANDLER: TO_HAND (context=7) — choose cards to add to hand from search
# ─────────────────────────────────────────────────────────────────────────────

def handle_to_hand(obs: Observation, options, min_count: int, max_count: int) -> list[int]:
    """
    Choose which card(s) to take into hand from search effects.
    Called by: Dawn (Basic+Stage1+Stage2), Ultra Ball, Poké Pad, etc.
    """
    state  = obs.current
    my_idx = state.yourIndex
    field  = _field_counts(state, my_idx)
    hand   = _hand_counts(state, my_idx)

    dragapult_in_field = field[DREEPY] + field[DRAKLOAK] + field[DRAGAPULT_EX]
    blaziken_in_field  = field[TORCHIC] + field[COMBUSKEN] + field[BLAZIKEN_EX]

    scores = []
    for o in options:
        card = _get_card(obs, o.area, o.index, my_idx)
        if not card:
            scores.append(0.0)
            continue

        cid   = card.id
        score = 100.0

        if cid == DRAGAPULT_EX:
            score = 9000.0 if dragapult_in_field >= 1 else 4000.0
        elif cid == BLAZIKEN_EX:
            score = 8000.0 if blaziken_in_field >= 1 else 3000.0
        elif cid == RARE_CANDY:
            score = 7500.0 if field[DREEPY] >= 1 else 2000.0
        elif cid == DREEPY:
            score = 5000.0 if dragapult_in_field < 3 else 500.0
        elif cid == DRAKLOAK:
            score = 4000.0 if field[DREEPY] >= 1 else 1000.0
        elif cid == TORCHIC:
            score = 4500.0 if blaziken_in_field < 2 else 500.0
        elif cid == COMBUSKEN:
            score = 3500.0 if field[TORCHIC] >= 1 else 800.0
        elif cid == PSYCHIC_ENERGY:
            score = 3500.0
        elif cid == FIRE_ENERGY:
            score = 3000.0
        elif cid == BOSS_ORDERS:
            score = 4000.0
        elif cid == CRISPIN:
            score = 3500.0
        elif cid in (LILLIE, DAWN):
            score = 2500.0
        elif cid in (ULTRA_BALL, BUDDY_POFFIN):
            score = 2000.0
        elif cid in (RISKY_RUINS, WATCHTOWER):
            score = 1500.0

        # Penalise duplicates already in hand
        score -= hand[cid] * 300.0
        scores.append(score)

    return _pick_best(scores, min_count, max_count)


# ─────────────────────────────────────────────────────────────────────────────
# HANDLER: DISCARD (context=8) — choose cards to discard (e.g. Ultra Ball cost)
# ─────────────────────────────────────────────────────────────────────────────

def handle_discard(obs: Observation, options, min_count: int, max_count: int) -> list[int]:
    """
    Ultra Ball requires discarding 2 cards.
    Discard the least valuable cards — excess energy or duplicate basics.
    """
    state  = obs.current
    my_idx = state.yourIndex
    hand   = _hand_counts(state, my_idx)
    field  = _field_counts(state, my_idx)

    scores = []
    for o in options:
        card = _get_card(obs, AreaType.HAND, o.index, my_idx)
        if not card:
            scores.append(0.0)
            continue

        cid = card.id
        # Higher discard score = more willing to discard this card
        # We invert scores here: pick HIGHEST scored = most expendable

        if cid == PSYCHIC_ENERGY:
            # Discard energy willingly — Crispin/Blaziken can recover it
            score = 800.0
        elif cid == FIRE_ENERGY:
            score = 700.0
        elif cid == DREEPY:
            # Only discard Dreepy if we have plenty in field
            dreepy_total = field[DREEPY] + field[DRAKLOAK] + field[DRAGAPULT_EX]
            score = 600.0 if dreepy_total >= 3 else 100.0
        elif cid == TORCHIC:
            blaziken_total = field[TORCHIC] + field[COMBUSKEN] + field[BLAZIKEN_EX]
            score = 500.0 if blaziken_total >= 2 else 50.0
        elif cid == RARE_CANDY:
            # Discard Rare Candy if Dreepy not in play
            score = 400.0 if field[DREEPY] == 0 else 50.0
        elif cid in (RISKY_RUINS, WATCHTOWER):
            # Stadiums are expendable if already in play
            score = 350.0
        elif cid == SWITCH:
            score = 300.0
        elif cid in (LILLIE, COLRESS, DAWN, CRISPIN):
            score = 150.0   # Supporters are valuable — discard last
        elif cid in (DRAGAPULT_EX, BLAZIKEN_EX):
            score = 20.0    # Never discard key Stage 2s if avoidable
        elif cid in (BOSS_ORDERS, ULTRA_BALL, BUDDY_POFFIN):
            score = 200.0
        else:
            score = 250.0

        scores.append(score)

    return _pick_best(scores, min_count, max_count)


# ─────────────────────────────────────────────────────────────────────────────
# HANDLER: ATTACH_FROM (context=21) — choose WHICH energy to attach
# ─────────────────────────────────────────────────────────────────────────────

def handle_attach_from(obs: Observation, options, min_count: int, max_count: int) -> list[int]:
    """
    Choose which energy card from hand to attach.
    We track the choice so ATTACH_TO knows what energy is being placed.
    """
    global _last_attach_card_id
    state  = obs.current
    my_idx = state.yourIndex
    field  = _field_counts(state, my_idx)

    active = state.players[my_idx].active[0] if state.players[my_idx].active else None

    scores = []
    for o in options:
        card = _get_card(obs, AreaType.HAND, o.index, my_idx)
        if not card:
            scores.append(0.0)
            continue

        cid = card.id
        score = 0.0

        if cid == PSYCHIC_ENERGY:
            # Psychic goes to Dragapult line
            if active and active.id == DRAGAPULT_EX:
                has_fire = _has_energy(active, EnergyType.FIRE)
                if has_fire:
                    score = 9000.0   # Dragapult has Fire — add Psychic to complete
                else:
                    score = 7000.0
            elif active and active.id in (DREEPY, DRAKLOAK):
                score = 6000.0
            else:
                score = 3000.0

        elif cid == FIRE_ENERGY:
            # Fire goes to Dragapult (for Phantom Dive) or Blaziken
            if active and active.id == DRAGAPULT_EX:
                has_psychic = _has_energy(active, EnergyType.PSYCHIC)
                if has_psychic:
                    score = 9000.0   # Dragapult has Psychic — add Fire to complete
                else:
                    score = 7500.0
            elif active and active.id == BLAZIKEN_EX:
                fire_count = sum(1 for e in getattr(active, 'energies', [])
                               if e == EnergyType.FIRE)
                score = 7000.0 if fire_count < 3 else 2000.0
            else:
                score = 4000.0

        scores.append(score)

    # Track which energy we chose for ATTACH_TO handler
    if scores and options:
        best_idx = _pick_best(scores, min_count, max_count)[0]
        card = _get_card(obs, AreaType.HAND, options[best_idx].index, my_idx)
        if card:
            _last_attach_card_id = card.id

    return _pick_best(scores, min_count, max_count)


# ─────────────────────────────────────────────────────────────────────────────
# HANDLER: ATTACH_TO (context=22) — choose WHICH Pokémon to attach energy to
# This was the biggest unhandled context — firing 15x per game randomly
# ─────────────────────────────────────────────────────────────────────────────

def handle_attach_to(obs: Observation, options, min_count: int, max_count: int) -> list[int]:
    """
    Choose which Pokémon to attach the selected energy to.
    Uses _last_attach_card_id to know which energy type we're placing.
    """
    state  = obs.current
    my_idx = state.yourIndex
    energy_id = _last_attach_card_id

    scores = []
    for o in options:
        poke = _get_card(obs, o.inPlayArea if hasattr(o, 'inPlayArea') else AreaType.BENCH,
                         o.inPlayIndex if hasattr(o, 'inPlayIndex') else o.index, my_idx)
        if not poke:
            # Try active
            poke = _get_card(obs, AreaType.BENCH, o.index, my_idx)
        if not poke:
            scores.append(0.0)
            continue

        scores.append(_energy_score(energy_id, poke))

    return _pick_best(scores, min_count, max_count)


# ─────────────────────────────────────────────────────────────────────────────
# HANDLER: DISCARD_ENERGY (context=30)
# ─────────────────────────────────────────────────────────────────────────────

def handle_discard_energy(obs: Observation, options, min_count: int, max_count: int) -> list[int]:
    """
    Choose which energy to discard (e.g. retreat cost, some attack effects).
    Prefer discarding Fire energy — Blaziken can recover it from discard.
    Avoid discarding Psychic if Dragapult needs it.
    """
    state  = obs.current
    my_idx = state.yourIndex

    scores = []
    for o in options:
        card = _get_card(obs, o.area if hasattr(o, 'area') else AreaType.ACTIVE,
                        o.index, my_idx)
        if not card:
            scores.append(500.0)  # Default — pick something
            continue

        cid = getattr(card, 'id', 0)
        if cid == FIRE_ENERGY:
            score = 900.0   # Discard Fire first — Blaziken recovers it
        elif cid == PSYCHIC_ENERGY:
            score = 600.0   # Psychic less recoverable
        else:
            score = 400.0

        scores.append(score)

    return _pick_best(scores, min_count, max_count)


# ─────────────────────────────────────────────────────────────────────────────
# HANDLER: EVOLVE (context=37) — choose which Pokémon to evolve
# ─────────────────────────────────────────────────────────────────────────────

def handle_evolve(obs: Observation, options, min_count: int, max_count: int) -> list[int]:
    """
    Choose which in-play Pokémon to evolve.
    Priority: evolve the one with most energy attached first.
    Prefer active over bench if it can attack immediately after evolution.
    """
    state  = obs.current
    my_idx = state.yourIndex

    scores = []
    for o in options:
        # The target is the Pokémon being evolved (in play)
        area  = o.inPlayArea if hasattr(o, 'inPlayArea') else AreaType.BENCH
        index = o.inPlayIndex if hasattr(o, 'inPlayIndex') else o.index
        poke  = _get_card(obs, area, index, my_idx)

        if not poke:
            scores.append(0.0)
            continue

        energy = _energy_count(poke)
        is_active = (area == AreaType.ACTIVE)
        score = energy * 500.0      # More energy = higher priority (can attack sooner)
        if is_active:
            score += 300.0          # Active Pokémon slightly preferred
        scores.append(score)

    return _pick_best(scores, min_count, max_count)


# ─────────────────────────────────────────────────────────────────────────────
# HANDLER: TO_ACTIVE — choose which benched Pokémon becomes Active
# ─────────────────────────────────────────────────────────────────────────────

def handle_to_active(obs: Observation, options, min_count: int, max_count: int) -> list[int]:
    """After a KO, choose the best replacement. Dragapult ex with both energy = top priority."""
    state  = obs.current
    my_idx = state.yourIndex

    scores = []
    for o in options:
        poke = _get_card(obs, AreaType.BENCH, o.index, my_idx)
        if not poke:
            scores.append(0.0)
            continue

        energy  = _energy_count(poke)
        hp_left = _hp_remaining(poke)

        if poke.id == DRAGAPULT_EX:
            if _dragapult_ready(poke):
                score = 10000.0     # Ready to attack immediately
            elif _dragapult_one_away(poke):
                score = 7000.0
            else:
                score = 4000.0
        elif poke.id == BLAZIKEN_EX:
            score = 3500.0 + energy * 100
        elif poke.id == DRAKLOAK:
            score = 3000.0 + energy * 100
        elif poke.id == DREEPY:
            score = 1000.0
        elif poke.id in (TORCHIC, COMBUSKEN):
            score = 800.0
        else:
            score = 500.0

        if hp_left <= 30:
            score -= 2000.0  # Don't send up near-dead Pokémon

        scores.append(score)

    return _pick_best(scores, min_count, max_count)


# ─────────────────────────────────────────────────────────────────────────────
# HANDLER: GENERIC — catch-all
# ─────────────────────────────────────────────────────────────────────────────

def handle_generic(obs: Observation, options, min_count: int, max_count: int) -> list[int]:
    context = getattr(obs.select, 'context', 'UNKNOWN')
    print(f"[UNHANDLED CONTEXT: {context}] — using random pick")
    return _safe_fallback(options, min_count)
