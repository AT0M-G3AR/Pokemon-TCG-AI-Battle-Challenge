"""
PTCG AI Battle Challenge — v3 Alakazam + Dudunsparce Policy
AT0M-G3AR | Gary & Team | 2026

DECK: Alakazam (Powerful Hand) + Dudunsparce (Run Away Draw)
WIN CONDITION: Powerful Hand — 2 damage counters per card in hand (uncapped)

THREE CORE RULES:
  1. Calculate lethal BEFORE playing any cards — stop playing once KO is secured
  2. Dudunsparce Run Away Draw is always top priority (score 15000)
  3. Enhanced Hammer removes Mist Energy before attacking

KEY CARD IDS:
  Pokémon:  Abra=741, Kadabra=742, Alakazam=743, Alakazam_TWM=245
            Dunsparce=305, Dudunsparce=66, Shaymin=343
  Trainers: Poffin=1086, RareCandy=1079, EnhancedHammer=1081
            PokeePad=1152, NightStretcher=1097, SacredAsh=1129
            BossOrders=1182, LanasAid=1184, Hilda=1225
            Dawn=1231, BattleCage=1264
  Energy:   Psychic=5, Telepath=19, Enriching=13 (ACE SPEC)
  Special:  MistEnergy=11, RockyFighting=? (blocks damage counters)
"""

import random
from collections import defaultdict
from cg.api import (
    Observation, SelectContext, OptionType, AreaType,
    CardType, EnergyType, Card, Pokemon, all_card_data, to_observation_class
)

# ─────────────────────────────────────────────────────────────────────────────
# CARD DATABASE
# ─────────────────────────────────────────────────────────────────────────────
CARD_DB = {c.cardId: c for c in all_card_data()}

# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────
ABRA         = 109   # TWM — Teleporter free pivot
KADABRA      = 742
ALAKAZAM     = 743   # Powerful Hand — main attacker
ALAKAZAM_TWM = 245   # Strange Hacking tech
DUNSPARCE    = 65    # TEF — zero retreat cost
DUDUNSPARCE  = 66
SHAYMIN      = 343

POFFIN        = 1086
RARE_CANDY    = 1079
ENH_HAMMER    = 1081
POKE_PAD      = 1152
NIGHT_STRETCH = 1097
SACRED_ASH    = 1129
BOSS_ORDERS   = 1182
LANAS_AID     = 1184
HILDA         = 1225
DAWN          = 1231
BATTLE_CAGE   = 1264

PSYCHIC_ENERGY  = 5
TELEPATH_ENERGY = 19
ENRICHING_ENERGY= 13
MIST_ENERGY     = 11   # Blocks damage counter effects — must hammer this

ALAKAZAM_LINE = {ABRA, KADABRA, ALAKAZAM, ALAKAZAM_TWM}
DUNSPARCE_LINE = {DUNSPARCE, DUDUNSPARCE}

# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _safe_fallback(options, min_count):
    count = max(1, min(min_count, len(options)))
    return random.sample(list(range(len(options))), count)


def _pick_best(scores, min_count, max_count):
    indexed = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)
    valid = [i for i, s in indexed if s > -9000]
    if not valid:
        valid = [indexed[0][0]] if indexed else [0]
    count = max(min_count, 1)
    count = min(count, len(valid), max_count)
    return [i for i, _ in indexed[:count]]


def _prize_count(pokemon):
    data = CARD_DB.get(pokemon.id)
    if not data:
        return 1
    return 3 if getattr(data, 'megaEx', False) else 2 if getattr(data, 'ex', False) else 1


def _hp_remaining(pokemon):
    return max(0, pokemon.hp - getattr(pokemon, 'damage', 0))


def _energy_count(pokemon):
    return len(getattr(pokemon, 'energies', []))


def _get_card(obs, area, index, player_index):
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


def _hand_counts(state, player_index):
    counts = defaultdict(int)
    for c in state.players[player_index].hand:
        counts[c.id] += 1
    return counts


def _field_counts(state, player_index):
    counts = defaultdict(int)
    active = state.players[player_index].active
    if active and active[0]:
        counts[active[0].id] += 1
    for p in state.players[player_index].bench:
        if p:
            counts[p.id] += 1
    return counts


def _discard_counts(state, player_index):
    counts = defaultdict(int)
    for c in state.players[player_index].discard:
        counts[c.id] += 1
    return counts


def _opponent_has_mist_energy(state, op_idx):
    """Check if opponent's active has Mist Energy attached."""
    op_active = state.players[op_idx].active
    if not op_active or not op_active[0]:
        return False
    energies = getattr(op_active[0], 'energyCards', [])
    for e in energies:
        if getattr(e, 'id', 0) == MIST_ENERGY:
            return True
    return False


def _powerful_hand_damage(hand_size):
    """Powerful Hand places 2 damage counters per card = 20 damage per card."""
    return hand_size * 20


def _achievable_hand_size(state, my_idx):
    """
    Estimate hand size we can achieve this turn.
    Current hand + 3 if Dudunsparce is benched (Run Away Draw) + 1 from supporter.
    """
    hand_size = len(state.players[my_idx].hand)
    # Add 3 if Dudunsparce is benched (we'll use Run Away Draw)
    for p in state.players[my_idx].bench:
        if p and p.id == DUDUNSPARCE:
            hand_size += 3
            break
    return hand_size


def _lethal_now(state, my_idx, op_idx):
    """
    Can we KO the opponent's active RIGHT NOW without playing more cards?
    If yes — stop playing cards, just attack.
    """
    op_active = state.players[op_idx].active
    if not op_active or not op_active[0]:
        return False
    hp_left = _hp_remaining(op_active[0])
    hand_size = len(state.players[my_idx].hand)
    damage = _powerful_hand_damage(hand_size)
    return damage >= hp_left


def _target_score(pokemon, my_prizes_left):
    if pokemon is None:
        return -9999.0
    prizes = _prize_count(pokemon)
    hp_left = _hp_remaining(pokemon)
    score = prizes * 1000.0
    score += _energy_count(pokemon) * 150.0
    score -= hp_left * 0.3
    if prizes >= my_prizes_left:
        score += 50000.0
    return score


# ─────────────────────────────────────────────────────────────────────────────
# ROUTER
# ─────────────────────────────────────────────────────────────────────────────

def select_action(obs: Observation) -> list[int]:
    context   = obs.select.context
    options   = obs.select.option
    min_count = obs.select.minCount
    max_count = obs.select.maxCount

    if not options:
        return []

    try:
        handlers = {
            SelectContext.MAIN:                  handle_main,
            SelectContext.SETUP_ACTIVE_POKEMON:  handle_setup_active,
            SelectContext.SETUP_BENCH_POKEMON:   handle_setup_bench,
            SelectContext.TO_BENCH:              handle_to_bench,
            SelectContext.TO_HAND:               handle_to_hand,
            SelectContext.DISCARD:               handle_discard,
            SelectContext.SWITCH:                handle_to_active,
            SelectContext.TO_ACTIVE:             handle_to_active,
            SelectContext.ATTACH_FROM:           handle_attach_from,
            SelectContext.ATTACH_TO:             handle_attach_to,
            SelectContext.DISCARD_ENERGY:        handle_discard_energy,
            SelectContext.EVOLVE:                handle_evolve,
            SelectContext.DAMAGE_COUNTER:        handle_damage_counter,
            SelectContext.DAMAGE_COUNTER_ANY:    handle_damage_counter,
            SelectContext.DAMAGE_COUNTER_COUNT:  handle_damage_counter_count,
            SelectContext.TO_HAND_ENERGY:        handle_to_hand_energy,
            SelectContext.ACTIVATE:              handle_activate,
            SelectContext.IS_FIRST:              handle_is_first,
            SelectContext.DRAW_COUNT:            handle_draw_count,
        }
        handler = handlers.get(context, handle_generic)
        return handler(obs, options, min_count, max_count)
    except Exception as e:
        print(f"[policy error] ctx={context} err={e}")
        return _safe_fallback(options, min_count)


# ─────────────────────────────────────────────────────────────────────────────
# HANDLE MAIN — the most important function
# Core logic: check lethal first, Dudunsparce draws, then set up
# ─────────────────────────────────────────────────────────────────────────────

def handle_main(obs, options, min_count, max_count):
    state    = obs.current
    my_idx   = state.yourIndex
    op_idx   = 1 - my_idx
    my_state = state.players[my_idx]
    op_state = state.players[op_idx]
    my_prizes = len(my_state.prize)

    hand    = _hand_counts(state, my_idx)
    field   = _field_counts(state, my_idx)
    discard = _discard_counts(state, my_idx)

    supporter_played = getattr(state, 'supporterPlayed', False)
    energy_attached  = getattr(state, 'energyAttached', False)

    active    = my_state.active[0] if my_state.active else None
    op_active = op_state.active[0] if op_state.active else None
    op_bench  = [p for p in op_state.bench if p is not None]

    bench_space = 5 - sum(1 for p in my_state.bench if p is not None)
    hand_size   = len(my_state.hand)

    # ── LETHAL CHECK ────────────────────────────────────────────────────────
    # If we can KO opponent's active right now, ONLY score the attack
    is_lethal = _lethal_now(state, my_idx, op_idx)
    mist_on_opponent = _opponent_has_mist_energy(state, op_idx)

    # Achievable hand damage after drawing with Dudunsparce
    achievable = _achievable_hand_size(state, my_idx)
    op_hp = _hp_remaining(op_active) if op_active else 999
    can_lethal_after_draw = _powerful_hand_damage(achievable) >= op_hp

    alakazam_line_field = (field[ABRA] + field[KADABRA] +
                           field[ALAKAZAM] + field[ALAKAZAM_TWM])
    dunsparce_field = field[DUNSPARCE] + field[DUDUNSPARCE]

    scores = []
    for o in options:

        # ── ATTACK ──────────────────────────────────────────────────────────
        if o.type == OptionType.ATTACK:
            if active and active.id == ALAKAZAM:
                if mist_on_opponent:
                    # Powerful Hand blocked — use Strange Hacking if available
                    # or just score low
                    score = 500.0
                elif is_lethal:
                    score = 20000.0  # Always attack for the KO
                elif can_lethal_after_draw:
                    score = 18000.0  # Draw first then attack
                else:
                    score = 8000.0   # Attack anyway — deal damage
            elif active and active.id == ALAKAZAM_TWM:
                # Strange Hacking — use when opponent has Mist Energy
                if mist_on_opponent:
                    score = 15000.0
                else:
                    score = 3000.0
            else:
                score = 2000.0

        # ── ABILITY ─────────────────────────────────────────────────────────
        elif o.type == OptionType.ABILITY:
            card = _get_card(obs, o.area if hasattr(o, 'area') else AreaType.BENCH,
                            o.index, my_idx)
            if card and card.id == DUDUNSPARCE:
                # Run Away Draw — ALWAYS highest priority
                # Draw 3 cards then shuffle Dudunsparce back in
                # Exception: if already lethal, don't draw (reduces hand size after shuffle)
                if is_lethal:
                    score = -9999.0  # Don't draw if already lethal!
                else:
                    score = 15000.0
            elif card and card.id in (KADABRA, ALAKAZAM):
                # Psychic Draw on evolve — handled separately
                score = 12000.0
            elif card and card.id == ABRA:
                # Teleporter ability
                # NEVER use if bench is empty (instant loss by bench out)
                if bench_space == 5:  # Means 0 bench Pokemon (5 spaces available)
                    score = -9999.0
                else:
                    # Use to pivot to a stronger Pokemon on the bench
                    score = 11000.0
            else:
                score = 5000.0

        # ── EVOLVE ──────────────────────────────────────────────────────────
        elif o.type == OptionType.EVOLVE:
            card = _get_card(obs, AreaType.HAND, o.index, my_idx)
            if card:
                if card.id == KADABRA:
                    score = 9500.0  # HIGHER than Rare Candy — draw 2 first
                elif card.id == ALAKAZAM:
                    score = 9000.0  # Then evolve to Alakazam for draw 3
                elif card.id == ALAKAZAM_TWM:
                    score = 7000.0 if mist_on_opponent else 4000.0
                else:
                    score = 3000.0

        # ── PLAY CARD ────────────────────────────────────────────────────────
        elif o.type == OptionType.PLAY:
            card = _get_card(obs, AreaType.HAND, o.index, my_idx)
            if not card:
                score = 0.0
            else:
                data = CARD_DB.get(card.id)
                card_type = getattr(data, 'cardType', None)
                cid = card.id

                # ── Pokémon to bench ────────────────────────────────────────
                if data and card_type == CardType.POKEMON:
                    if cid == ABRA:
                        score = 6000.0 if alakazam_line_field < 3 and bench_space > 0 else -9999.0
                    elif cid == DUNSPARCE:
                        score = 5500.0 if dunsparce_field < 3 and bench_space > 0 else -9999.0
                    elif cid == SHAYMIN:
                        # Bench protection against spread — situational
                        score = 3000.0 if bench_space > 0 else -9999.0
                    else:
                        score = 2000.0 if bench_space > 0 else -9999.0

                # ── Trainer cards ────────────────────────────────────────────
                else:
                    # STOP playing cards if lethal — every card = -20 damage
                    if is_lethal and cid not in (ENH_HAMMER, BOSS_ORDERS):
                        score = -9999.0
                        scores.append(score)
                        continue

                    if cid == ENH_HAMMER:
                        # Remove opponent's special energy (especially Mist Energy)
                        if mist_on_opponent:
                            score = 19000.0  # Highest priority — unblocks Powerful Hand
                        else:
                            # Still useful to remove other special energy
                            op_has_special = any(
                                getattr(e, 'id', 0) not in (5, 2, 1, 3, 4, 6, 7, 8, 9)
                                for p in [op_active] + op_bench if p
                                for e in getattr(p, 'energyCards', [])
                            )
                            score = 5000.0 if op_has_special else -9999.0

                    elif cid == RARE_CANDY:
                        abra_in_play = field[ABRA] > 0
                        alakazam_in_hand = hand[ALAKAZAM] > 0
                        kadabra_missing = field[KADABRA] == 0
                        if abra_in_play and alakazam_in_hand and kadabra_missing:
                            score = 7000.0  # Skip Kadabra — instant Stage 2
                        else:
                            score = -9999.0

                    elif cid == POFFIN:
                        # Search Abra + Dunsparce simultaneously
                        needs_abra     = alakazam_line_field < 2
                        needs_dunsparce = dunsparce_field < 2
                        if bench_space >= 1 and (needs_abra or needs_dunsparce):
                            score = 7500.0
                        elif bench_space >= 1:
                            score = 2000.0
                        else:
                            score = -9999.0

                    elif cid == DAWN:
                        # Dawn finds Basic + Stage1 + Stage2 = 3 cards into hand
                        # ALWAYS valuable — more cards = more Powerful Hand damage
                        # Play BEFORE other supporters to maximize hand size
                        if not supporter_played:
                            hand_size = len(my_state.hand)
                            missing_pieces = (
                                alakazam_line_field < 3 or
                                (field[ABRA] < 1 and hand[ABRA] < 1) or
                                (field[ALAKAZAM] < 2 and hand[ALAKAZAM] < 1)
                            )
                            if missing_pieces:
                                score = 8500.0   # Missing pieces — high priority
                            elif hand_size <= 6:
                                score = 7000.0   # Small hand — draw for damage
                            elif hand_size <= 9:
                                score = 5000.0   # Medium hand — still useful
                            else:
                                score = 2000.0   # Big hand — low priority
                        else:
                            score = -9999.0

                    elif cid == HILDA:
                        # Search Evolution + Energy
                        if not supporter_played:
                            needs_alakazam = field[ALAKAZAM] + hand[ALAKAZAM] < 2
                            if needs_alakazam:
                                score = 7500.0
                            else:
                                score = 4000.0
                        else:
                            score = -9999.0

                    elif cid == BOSS_ORDERS:
                        # Gust best target — only if we can KO it
                        if not supporter_played and op_bench:
                            best = max(_target_score(p, my_prizes) for p in op_bench)
                            active_val = _target_score(op_active, my_prizes) if op_active else 0
                            if best > active_val + 300:
                                score = 7000.0
                            else:
                                score = -9999.0
                        else:
                            score = -9999.0

                    elif cid == LANAS_AID:
                        # Put up to 3 non-Rule Box Pokémon from discard to hand
                        # Inflates hand size for surprise Powerful Hand KO
                        alakazam_in_discard = discard[ABRA] + discard[KADABRA] + discard[ALAKAZAM]
                        dunsparce_in_discard = discard[DUNSPARCE] + discard[DUDUNSPARCE]
                        if not supporter_played:
                            if alakazam_in_discard + dunsparce_in_discard >= 2:
                                score = 6500.0  # Recover + inflate hand
                            elif alakazam_in_discard >= 1:
                                score = 5000.0
                            else:
                                score = -9999.0
                        else:
                            score = -9999.0

                    elif cid == POKE_PAD:
                        # Search non-Rule Box Pokémon — finds Abra, Dunsparce
                        if alakazam_line_field < 2 or dunsparce_field < 1:
                            score = 6000.0
                        else:
                            score = 2000.0

                    elif cid == NIGHT_STRETCH:
                        # Recover Pokémon from discard
                        alakazam_lost = discard[ALAKAZAM]
                        abra_lost = discard[ABRA]
                        if alakazam_lost >= 1:
                            score = 5500.0
                        elif abra_lost >= 1:
                            score = 4000.0
                        else:
                            score = 1000.0

                    elif cid == SACRED_ASH:
                        # Recover up to 5 Pokémon from discard to deck
                        total_in_discard = sum(discard[c] for c in
                            [ABRA, KADABRA, ALAKAZAM, DUNSPARCE, DUDUNSPARCE])
                        if total_in_discard >= 3:
                            score = 5000.0
                        elif total_in_discard >= 2:
                            score = 3000.0
                        else:
                            score = -9999.0

                    elif cid == BATTLE_CAGE:
                        # Check if opponent has a stadium that benefits them
                        current_stadium = getattr(state, 'stadium', None)
                        if current_stadium and getattr(current_stadium, 'playerIndex', my_idx) != my_idx:
                            score = 8000.0  # Replace opponent's stadium immediately
                        else:
                            score = 2500.0

                    else:
                        score = 1000.0

        # ── ATTACH ENERGY ────────────────────────────────────────────────────
        elif o.type == OptionType.ATTACH:
            if not energy_attached:
                card   = _get_card(obs, AreaType.HAND, o.index, my_idx)
                target = _get_card(obs, o.inPlayArea, o.inPlayIndex, my_idx)
                if card and target:
                    # Always attach to Alakazam first
                    if target.id == ALAKAZAM:
                        score = 9000.0
                    elif target.id == ALAKAZAM_TWM:
                        score = 8000.0
                    elif target.id == KADABRA:
                        score = 5000.0
                    elif target.id == ABRA:
                        score = 3000.0
                    else:
                        score = 500.0
                else:
                    score = 0.0
            else:
                score = -9999.0

        # ── RETREAT ─────────────────────────────────────────────────────────
        elif o.type == OptionType.RETREAT:
            if active and active.id not in (ALAKAZAM, ALAKAZAM_TWM):
                # Get Alakazam to active
                alakazam_ready = any(
                    p and p.id == ALAKAZAM and _energy_count(p) >= 1
                    for p in my_state.bench if p
                )
                score = 4000.0 if alakazam_ready else 500.0
            else:
                score = -9999.0  # Never retreat Alakazam

        # ── END ─────────────────────────────────────────────────────────────
        elif o.type == OptionType.END:
            # End turn — but only if we've attacked or have nothing else to do
            score = -5000.0

        else:
            score = 0.0

        scores.append(score)

    return _pick_best(scores, min_count, max_count)


# ─────────────────────────────────────────────────────────────────────────────
# HANDLE ACTIVATE — Dudunsparce Run Away Draw + Kadabra/Alakazam Psychic Draw
# ─────────────────────────────────────────────────────────────────────────────

def handle_activate(obs, options, min_count, max_count):
    """Always YES to abilities in this deck — all abilities are beneficial."""
    state  = obs.current
    my_idx = state.yourIndex
    op_idx = 1 - my_idx

    is_lethal = _lethal_now(state, my_idx, op_idx)

    scores = []
    for o in options:
        if o.type == OptionType.YES:
            # Check if this is Dudunsparce's ability
            card = _get_card(obs, o.area if hasattr(o, 'area') else AreaType.BENCH,
                           o.index, my_idx)
            
            if card and card.id == DUDUNSPARCE and is_lethal:
                score = -9999.0  # Don't draw if we're already lethal!
            elif card and card.id == ABRA:
                # Teleporter ACTIVATE confirmation
                bench_empty = all(p is None for p in state.players[my_idx].bench)
                if bench_empty:
                    score = -9999.0  # NEVER shuffle if no bench
                else:
                    score = 9000.0
            else:
                score = 9000.0
        else:
            score = -9000.0
        scores.append(score)
    return _pick_best(scores, min_count, max_count)


# ─────────────────────────────────────────────────────────────────────────────
# HANDLE SETUP_ACTIVE
# ─────────────────────────────────────────────────────────────────────────────

def handle_setup_active(obs, options, min_count, max_count):
    """Start with Abra as active — it's our main evolution target."""
    my_idx = obs.current.yourIndex
    scores = []
    for o in options:
        card = _get_card(obs, AreaType.HAND, o.index, my_idx)
        if not card:
            scores.append(0.0)
            continue
        if card.id == ABRA:         scores.append(100.0)
        elif card.id == DUNSPARCE:  scores.append(60.0)
        elif card.id == DUDUNSPARCE: scores.append(40.0)
        else:                        scores.append(10.0)
    return _pick_best(scores, min_count, max_count)


# ─────────────────────────────────────────────────────────────────────────────
# HANDLE SETUP_BENCH
# ─────────────────────────────────────────────────────────────────────────────

def handle_setup_bench(obs, options, min_count, max_count):
    """Fill bench with Abra x2 + Dunsparce x2 minimum."""
    state  = obs.current
    my_idx = state.yourIndex
    field  = _field_counts(state, my_idx)

    scores = []
    for o in options:
        card = _get_card(obs, AreaType.HAND, o.index, my_idx)
        if not card:
            scores.append(0.0)
            continue
        if card.id == ABRA:
            scores.append(100.0 if field[ABRA] < 3 else 20.0)
        elif card.id == DUNSPARCE:
            scores.append(80.0 if field[DUNSPARCE] < 3 else 10.0)
        elif card.id == DUDUNSPARCE:
            scores.append(70.0)
        else:
            scores.append(20.0)
    return _pick_best(scores, min_count, max_count)


# ─────────────────────────────────────────────────────────────────────────────
# HANDLE TO_BENCH (context 5)
# ─────────────────────────────────────────────────────────────────────────────

def handle_to_bench(obs, options, min_count, max_count):
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
        if card.id == ABRA:
            scores.append(100.0 if field[ABRA] < 3 else 20.0)
        elif card.id == DUNSPARCE:
            scores.append(80.0 if field[DUNSPARCE] < 3 else 10.0)
        elif card.id == DUDUNSPARCE:
            scores.append(70.0)
        else:
            scores.append(30.0)
    return _pick_best(scores, min_count, max_count)


# ─────────────────────────────────────────────────────────────────────────────
# HANDLE TO_HAND (context 7) — search effects
# ─────────────────────────────────────────────────────────────────────────────

def handle_to_hand(obs, options, min_count, max_count):
    """
    Choose which card to take into hand from search effects.
    Dawn: pick Basic + Stage1 + Stage2 → Abra + Kadabra + Alakazam
    Hilda: pick Evolution + Energy → Alakazam + Psychic Energy
    Poffin: pick Abra + Dunsparce
    """
    state  = obs.current
    my_idx = state.yourIndex
    field  = _field_counts(state, my_idx)
    hand   = _hand_counts(state, my_idx)

    alakazam_in_field = field[ABRA] + field[KADABRA] + field[ALAKAZAM]

    scores = []
    for o in options:
        card = _get_card(obs, o.area, o.index, my_idx)
        if not card:
            scores.append(0.0)
            continue

        cid = card.id
        score = 100.0

        if cid == ALAKAZAM:
            score = 9000.0 if alakazam_in_field >= 1 else 5000.0
        elif cid == KADABRA:
            score = 8000.0 if field[ABRA] >= 1 else 3000.0
        elif cid == ABRA:
            score = 7000.0 if alakazam_in_field < 3 else 1000.0
        elif cid == DUDUNSPARCE:
            score = 6000.0 if field[DUDUNSPARCE] < 1 else 2000.0
        elif cid == DUNSPARCE:
            score = 5000.0 if field[DUNSPARCE] < 3 else 500.0
        elif cid == RARE_CANDY:
            score = 7500.0 if field[ABRA] >= 1 else 2000.0
        elif cid in (PSYCHIC_ENERGY, TELEPATH_ENERGY):
            score = 4000.0
        elif cid == ENRICHING_ENERGY:
            score = 5000.0  # ACE SPEC — always valuable
        elif cid == BOSS_ORDERS:
            score = 5000.0
        elif cid == ENH_HAMMER:
            score = 4500.0
        elif cid in (DAWN, HILDA, LANAS_AID):
            score = 3500.0
        elif cid == POFFIN:
            score = 3000.0

        score -= hand[cid] * 300.0
        scores.append(score)

    return _pick_best(scores, min_count, max_count)


# ─────────────────────────────────────────────────────────────────────────────
# HANDLE DISCARD (context 8) — Ultra Ball cost, etc.
# ─────────────────────────────────────────────────────────────────────────────

def handle_discard(obs, options, min_count, max_count):
    """
    Choose cards to discard.
    Prefer discarding energy (recoverable) over key Pokémon.
    """
    state  = obs.current
    my_idx = state.yourIndex
    hand   = _hand_counts(state, my_idx)
    field  = _field_counts(state, my_idx)

    scores = []
    for o in options:
        card = _get_card(obs, AreaType.HAND, o.index, my_idx)
        if not card:
            scores.append(500.0)
            continue

        cid = card.id
        # Higher score = more willing to discard
        if cid in (PSYCHIC_ENERGY, TELEPATH_ENERGY):
            score = 900.0  # Energy is recoverable
        elif cid == DUNSPARCE:
            score = 700.0 if field[DUNSPARCE] >= 2 else 200.0
        elif cid == ABRA:
            score = 600.0 if field[ABRA] >= 3 else 100.0
        elif cid == RARE_CANDY:
            score = 500.0 if field[ABRA] == 0 else 100.0
        elif cid == BATTLE_CAGE:
            score = 400.0
        elif cid in (ALAKAZAM, KADABRA):
            score = 50.0  # Never discard evolution targets willingly
        elif cid in (BOSS_ORDERS, ENH_HAMMER):
            score = 300.0
        else:
            score = 350.0

        scores.append(score)

    return _pick_best(scores, min_count, max_count)


# ─────────────────────────────────────────────────────────────────────────────
# HANDLE TO_ACTIVE — choose which bench Pokémon becomes active
# ─────────────────────────────────────────────────────────────────────────────

def handle_to_active(obs, options, min_count, max_count):
    """Send up Alakazam with energy first. Never send up Dunsparce."""
    state  = obs.current
    my_idx = state.yourIndex

    scores = []
    for o in options:
        poke = _get_card(obs, AreaType.BENCH, o.index, my_idx)
        if not poke:
            scores.append(0.0)
            continue

        energy = _energy_count(poke)
        hp_left = _hp_remaining(poke)

        if poke.id == ALAKAZAM:
            score = 10000.0 + energy * 500  # Always prefer Alakazam
        elif poke.id == ALAKAZAM_TWM:
            score = 8000.0 + energy * 300
        elif poke.id == KADABRA:
            score = 4000.0 + energy * 100
        elif poke.id == ABRA:
            score = 2000.0
        elif poke.id == DUDUNSPARCE:
            score = 1000.0  # Can use Run Away Draw to pivot back
        elif poke.id == DUNSPARCE:
            score = 500.0
        else:
            score = 300.0

        if hp_left <= 30:
            score -= 2000.0

        scores.append(score)

    return _pick_best(scores, min_count, max_count)


# ─────────────────────────────────────────────────────────────────────────────
# HANDLE ATTACH_FROM (context 21) — choose which energy to attach
# ─────────────────────────────────────────────────────────────────────────────

_last_energy_id = PSYCHIC_ENERGY

def handle_attach_from(obs, options, min_count, max_count):
    global _last_energy_id
    state  = obs.current
    my_idx = state.yourIndex

    scores = []
    for o in options:
        card = _get_card(obs, AreaType.HAND, o.index, my_idx)
        if not card:
            scores.append(0.0)
            continue
        # All energy types are Psychic variants — always attach
        score = 5000.0
        if card.id == ENRICHING_ENERGY:
            score = 6000.0  # Draw 4 cards when attached
        scores.append(score)

    if scores and options:
        best = _pick_best(scores, min_count, max_count)[0]
        card = _get_card(obs, AreaType.HAND, options[best].index, my_idx)
        if card:
            _last_energy_id = card.id

    return _pick_best(scores, min_count, max_count)


# ─────────────────────────────────────────────────────────────────────────────
# HANDLE ATTACH_TO (context 22) — choose which Pokémon to attach energy to
# ─────────────────────────────────────────────────────────────────────────────

def handle_attach_to(obs, options, min_count, max_count):
    """Always attach energy to Alakazam first."""
    state  = obs.current
    my_idx = state.yourIndex

    scores = []
    for o in options:
        area  = o.inPlayArea if hasattr(o, 'inPlayArea') else AreaType.BENCH
        index = o.inPlayIndex if hasattr(o, 'inPlayIndex') else o.index
        poke  = _get_card(obs, area, index, my_idx)
        if not poke:
            scores.append(0.0)
            continue
        if poke.id == ALAKAZAM:       scores.append(9000.0)
        elif poke.id == ALAKAZAM_TWM: scores.append(8000.0)
        elif poke.id == KADABRA:      scores.append(5000.0)
        elif poke.id == ABRA:         scores.append(2000.0)
        else:                          scores.append(500.0)
    return _pick_best(scores, min_count, max_count)


# ─────────────────────────────────────────────────────────────────────────────
# HANDLE EVOLVE (context 37)
# ─────────────────────────────────────────────────────────────────────────────

def handle_evolve(obs, options, min_count, max_count):
    """Evolve the Pokémon with most energy attached — can attack soonest."""
    state  = obs.current
    my_idx = state.yourIndex

    scores = []
    for o in options:
        area  = o.inPlayArea if hasattr(o, 'inPlayArea') else AreaType.BENCH
        index = o.inPlayIndex if hasattr(o, 'inPlayIndex') else o.index
        poke  = _get_card(obs, area, index, my_idx)
        if not poke:
            scores.append(0.0)
            continue
        energy  = _energy_count(poke)
        is_active = (area == AreaType.ACTIVE)
        score = energy * 500.0 + (300.0 if is_active else 0.0)
        scores.append(score)

    return _pick_best(scores, min_count, max_count)


# ─────────────────────────────────────────────────────────────────────────────
# HANDLE DAMAGE_COUNTER (context 13/14) — Powerful Hand places counters
# ─────────────────────────────────────────────────────────────────────────────

def handle_damage_counter(obs, options, min_count, max_count):
    """
    Choose where to place damage counters from Powerful Hand.
    Prioritize targets closest to KO, then highest prize value.
    """
    state     = obs.current
    my_idx    = state.yourIndex
    op_idx    = 1 - my_idx
    my_prizes = len(state.players[my_idx].prize)

    scores = []
    for o in options:
        target = None
        try:
            if hasattr(o, 'area') and o.area == AreaType.BENCH:
                target = state.players[op_idx].bench[o.index]
            elif hasattr(o, 'area') and o.area == AreaType.ACTIVE:
                target = state.players[op_idx].active[0]
        except (AttributeError, IndexError):
            pass

        if target is None:
            scores.append(-9999.0)
            continue

        hp_left = _hp_remaining(target)
        prizes  = _prize_count(target)
        score   = prizes * 1000.0
        score  += (1.0 - hp_left / max(target.hp, 1)) * 500.0
        score  += _energy_count(target) * 100.0
        if prizes >= my_prizes:
            score += 50000.0
        scores.append(score)

    return _pick_best(scores, min_count, max_count)


# ─────────────────────────────────────────────────────────────────────────────
# HANDLE DAMAGE_COUNTER_COUNT (context 39)
# ─────────────────────────────────────────────────────────────────────────────

def handle_damage_counter_count(obs, options, min_count, max_count):
    """Always place maximum damage counters — concentrate for KOs."""
    scores = []
    for o in options:
        number = getattr(o, 'number', 0)
        scores.append(float(number) * 1000.0)
    return _pick_best(scores, min_count, max_count)


# ─────────────────────────────────────────────────────────────────────────────
# HANDLE TO_HAND_ENERGY (context 31) — energy to hand after Crispin etc.
# ─────────────────────────────────────────────────────────────────────────────

def handle_to_hand_energy(obs, options, min_count, max_count):
    """Take Psychic energy to hand — always useful for Alakazam."""
    scores = []
    for o in options:
        card = _get_card(obs, o.area if hasattr(o, 'area') else AreaType.ACTIVE,
                        o.index, obs.current.yourIndex)
        if not card:
            scores.append(500.0)
            continue
        cid = getattr(card, 'id', 0)
        if cid == ENRICHING_ENERGY:
            scores.append(9000.0)  # ACE SPEC — highest value
        elif cid in (PSYCHIC_ENERGY, TELEPATH_ENERGY):
            scores.append(5000.0)
        else:
            scores.append(1000.0)
    return _pick_best(scores, min_count, max_count)


# ─────────────────────────────────────────────────────────────────────────────
# HANDLE DISCARD_ENERGY (context 30)
# ─────────────────────────────────────────────────────────────────────────────

def handle_discard_energy(obs, options, min_count, max_count):
    """Discard basic Psychic before special energy."""
    scores = []
    for o in options:
        card = _get_card(obs, o.area if hasattr(o, 'area') else AreaType.ACTIVE,
                        o.index, obs.current.yourIndex)
        cid = getattr(card, 'id', 0) if card else 0
        if cid == PSYCHIC_ENERGY:
            scores.append(900.0)   # Discard basic first
        elif cid == TELEPATH_ENERGY:
            scores.append(700.0)
        elif cid == ENRICHING_ENERGY:
            scores.append(100.0)   # Keep ACE SPEC as long as possible
        else:
            scores.append(500.0)
    return _pick_best(scores, min_count, max_count)


def handle_is_first(obs, options, min_count, max_count):
    # Going second = extra card draw = +20 Powerful Hand damage
    # Always choose second (index 1 if available, else 0)
    return [1] if len(options) > 1 else [0]


def handle_draw_count(obs, options, min_count, max_count):
    """
    Choose how many cards to draw (context 38).
    Always draw the maximum available — more cards = more Powerful Hand damage.
    """
    scores = []
    for o in options:
        number = getattr(o, 'number', 0)
        scores.append(float(number) * 1000.0)
    return _pick_best(scores, min_count, max_count)


# ─────────────────────────────────────────────────────────────────────────────
# HANDLE GENERIC — catch-all
# ─────────────────────────────────────────────────────────────────────────────

def handle_generic(obs, options, min_count, max_count):
    context = getattr(obs.select, 'context', 'UNKNOWN')
    print(f"[UNHANDLED CONTEXT: {context}] — random pick")
    return _safe_fallback(options, min_count)
