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
from search_api import (
    evaluate_attack,
    should_draw_before_attack,
    cards_needed_to_ko,
    calculate_powerful_hand_damage
)

# ─────────────────────────────────────────────────────────────────────────────
# CARD DATABASE
# ─────────────────────────────────────────────────────────────────────────────
CARD_DB = {c.cardId: c for c in all_card_data()}

# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────
ABRA         = 741
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
LILLIE_CLEFAIRY_EX = 272
SHAYMIN       = 343
XEROSIC       = 1197
NIGHTTIME_MINE = 1266
TEAM_ROCKETS_ARTICUNO = 414
DAMAGE_BLOCKING_ABILITY_IDS = {
    TEAM_ROCKETS_ARTICUNO,  # Repelling Veil
    74,  # Rabsca - Spherical Shield
    28,  # Poltchageist - Storehouse Hideaway
    203, # Skeledirge - Unaware
    835, # Empoleon ex - Emperor's Stance
    362, # Misty's Magikarp - So Submerged
    117, # Cornerstone Mask Ogerpon ex - Cornerstone Stance
    207, # Milotic ex - Sparkling Scales
}

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


def _pick_best(scores, min_count, max_count, allow_empty=False):
    indexed = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)
    valid = [i for i, s in indexed if s > -9000]
    
    if not valid:
        if allow_empty and min_count == 0:
            return []
        valid = [indexed[0][0]] if indexed else [0]
        
    # take as many valid options as allowed by max_count, respecting
    # min_count as a floor
    count = max(min_count, min(len(valid), max_count))
    if not allow_empty:
        count = max(count, 1)
        
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


def _deck_safety_discount(deck_count, draw_amount):
    """
    Graduated penalty for drawing cards when deck size is low.
    - Danger Zone: Drawing more cards than are in the deck (or leaving 0).
    - Critical: Leaving 1 card in the deck.
    - Warning: Leaving 2-3 cards in the deck.
    """
    remaining = deck_count - draw_amount
    discount = 0.0
    if remaining <= 0:
        discount = -9999.0
    elif remaining <= 1:
        discount = -5000.0
    elif remaining <= 3:
        discount = -2000.0
        
    if discount < 0:
        try:
            with open('deck_safety_log.txt', 'a') as f:
                f.write(f"DECK_SAFETY_FIRED: deck={deck_count}, draw={draw_amount}, rem={remaining}, disc={discount}\n")
        except:
            pass
    return discount


def _get_card(obs, area, index, player_index):
    ps = obs.current.players[player_index]
    try:
        match area:
            case AreaType.HAND:    return ps.hand[index]
            case AreaType.BENCH:   return ps.bench[index]
            case AreaType.ACTIVE:  return ps.active[index]
            case AreaType.DISCARD: return ps.discard[index]
            case AreaType.PRIZE:   return ps.prize[index]
            case AreaType.DECK:
                if obs.select and getattr(obs.select, 'deck', None) is not None:
                    return obs.select.deck[index]
                return None
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
    my_state = state.players[my_idx]
    op_active = state.players[op_idx].active
    
    if not op_active or not op_active[0]:
        return False
        
    my_active = my_state.active[0] if my_state.active else None
    
    # Check if Alakazam has the required 1 Psychic energy
    energy_count = _energy_count(my_active)
    if energy_count < 1:
        return False
        
    if not my_active or not op_active:
        return False
        
    if my_active.id == ALAKAZAM:
        if _opponent_has_mist_energy(state, op_idx):
            return False
            
        op_hp = _hp_remaining(op_active[0])
        hand_size = len(my_state.hand)
        return (hand_size * 20) >= op_hp
    
    return False


def _target_score(pokemon, my_prizes_left, current_damage=0):
    if pokemon is None:
        return -9999.0
    prizes = _prize_count(pokemon)
    hp_left = _hp_remaining(pokemon)
    score = prizes * 1000.0
    # Massively prioritize things we can actually kill
    if current_damage > 0 and hp_left <= current_damage:
        score += 10000.0
    
    if pokemon.id in DAMAGE_BLOCKING_ABILITY_IDS:
        score += 5000.0
        
    score += _energy_count(pokemon) * 150.0
    score -= hp_left * 0.3
    if prizes >= my_prizes_left and current_damage > 0 and hp_left <= current_damage:
        score += 50000.0
    return score

def has_damage_blocker_revealed(op_state):
    op_cards = op_state.active + op_state.bench
    for p in op_cards:
        if p and p.id in DAMAGE_BLOCKING_ABILITY_IDS:
            return True
    return False


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
            SelectContext.TO_DECK:               handle_to_deck,
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
        try:
            import traceback
            with open("/tmp/policy_error.log", "a") as f:
                f.write(f"--- [POLICY ERROR] Context: {context} ---\n")
                f.write(traceback.format_exc())
                f.write("\n")
        except:
            pass
        print(f"[policy error] ctx={context} err={e}", flush=True)
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
    post_disruption = hand_size <= 4

    # ── EARLY GAME / BENCH MATURITY SIGNAL ──────────────────────────────────
    # bench_filled counts non-empty bench slots; low bench_filled + basics
    # still in hand means board development should trump everything else,
    # including supporters. This is the missing signal that was causing
    # Dunsparce/Abra to sit in hand while Dawn/Hilda/Poffin got played instead.
    bench_filled = sum(1 for p in my_state.bench if p is not None)
    basics_in_hand = hand[ABRA] + hand[DUNSPARCE]
    early_game_undeveloped = bench_filled < 4 and basics_in_hand > 0

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

    alakazam_line_count = (
        field[ABRA] + field[KADABRA] + field[ALAKAZAM] + field[ALAKAZAM_TWM]
        + hand[ALAKAZAM]
    )
    board_is_saturated = (
        active is not None and active.id == ALAKAZAM and _energy_count(active) >= 1
        and alakazam_line_count >= 2
        and not is_lethal
    )

    # Bricked-hand detection: no Alakazam-line pieces anywhere to progress the board,
    # and no other draw/search engine in hand. Run Away Draw is the only lifeline.
    # A hand is ONLY unbricked if we actually have a playable Basic (Abra) or already have an Abra on board.
    # Having Kadabra/Alakazam in hand is useless if we have no Abra anywhere.
    have_usable_alakazam_line = (
        alakazam_line_field > 0 
        or hand[ABRA] > 0
    )
    has_other_draw_engine_in_hand = any(
        hand.get(c, 0) > 0 for c in (POFFIN, POKE_PAD, HILDA, DAWN)
    )
    hand_is_bricked = (
        not have_usable_alakazam_line
        and not has_other_draw_engine_in_hand
    )

    my_asleep = getattr(my_state, 'asleep', False)
    my_paralyzed = getattr(my_state, 'paralyzed', False)
    my_confused = getattr(my_state, 'confused', False)
    my_poisoned = getattr(my_state, 'poisoned', False)
    my_burned = getattr(my_state, 'burned', False)
    my_status_locked = my_asleep or my_paralyzed  # cannot retreat or use abilities
    my_status_curable_by_retreat = my_confused or my_poisoned or my_burned

    scores = []
    for o in options:

        # ── ATTACK ──────────────────────────────────────────────────────────
        if o.type == OptionType.ATTACK:
            if post_disruption and hand_size < 8 and not is_lethal:
                score = 2000.0  # Build hand first
            elif active and active.id == ALAKAZAM:
                hand_size = len(my_state.hand)
                op_hp = _hp_remaining(op_active) if op_active else 999
                try:
                    score = evaluate_attack(
                        obs,
                        o.index,
                        op_hp,
                        hand_size,
                        my_prizes,
                        len(op_state.prize),
                        len(op_bench)
                    )
                except Exception as e:
                    raise

                # v3.30: existing evolve discount
                attack_is_lethal_this_turn = (hand_size * 20) >= op_hp
                if not attack_is_lethal_this_turn:
                    has_unused_bench_evolve = any(
                        opt.type == OptionType.EVOLVE
                        and _get_card(obs, AreaType.HAND, opt.index, my_idx) is not None
                        and _get_card(obs, AreaType.HAND, opt.index, my_idx).id
                            in (KADABRA, ALAKAZAM, DUDUNSPARCE)
                        for opt in options
                    )
                    if has_unused_bench_evolve:
                        score = min(score, 9200.0)  # soft cap — just under EVOLVE's 9500

                    # v3.32 Fix 2: discount when a free, board-improving supporter
                    # (Dawn/Hilda) is available and unplayed this turn. Cap at 8400
                    # — below Dawn's minimum score of 8500 so Dawn always wins.
                    if not supporter_played:
                        has_useful_unplayed_supporter = any(
                            opt.type == OptionType.PLAY
                            and _get_card(obs, AreaType.HAND, opt.index, my_idx) is not None
                            and _get_card(obs, AreaType.HAND, opt.index, my_idx).id in (DAWN, HILDA)
                            for opt in options
                        )
                        if has_useful_unplayed_supporter:
                            score = min(score, 8400.0)  # below Dawn's 8500 minimum
            else:
                score = 3000.0

        # ── ABILITY ─────────────────────────────────────────────────────────
        elif o.type == OptionType.ABILITY:
            card = _get_card(obs, o.area if hasattr(o, 'area') else AreaType.BENCH,
                            o.index, my_idx)
            if card and card.id == DUDUNSPARCE:
                other_pokemon = 0
                if active is not None and active.id != DUDUNSPARCE:
                    other_pokemon += 1
                for p in my_state.bench:
                    if p and p.id != DUDUNSPARCE:
                        other_pokemon += 1

                hand_size = len(my_state.hand)
                op_hp = _hp_remaining(op_active) if op_active else 999
                
                if other_pokemon == 0:
                    score = -9999.0
                elif is_lethal:
                    score = -9999.0
                else:
                    alakazam_ready = any(
                        p and p.id == ALAKAZAM and _energy_count(p) >= 1
                        for p in ([active] if active else []) + list(my_state.bench)
                        if p
                    )
                    backfill_available = sum(
                        1 for p in my_state.bench
                        if p and p.id in (DUNSPARCE, DUDUNSPARCE)
                    ) >= 1
                    op_has_fighting = any(
                        getattr(p, 'pokemonType', -1) == 6 or p.id in (678, 674)
                        for p in ([op_active] if op_active else []) + list(op_bench)
                        if p
                    )

                    if board_is_saturated and backfill_available:
                        score = -9999.0  # backfill was the only justification; already redundant
                    elif alakazam_ready or backfill_available:
                        score = 15000.0  # keep existing high priority value used here
                    elif op_has_fighting:
                        score = 12000.0
                    elif hand_is_bricked:
                        score = 13000.0  # emergency draw — bricked hand, no other way forward
                    else:
                        score = -9999.0  # suppress — hold as tank instead
                    
                    if score > 0:
                        score += _deck_safety_discount(my_state.deckCount, 3)
                        if score < 0:
                            score = -9999.0
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
                elif card.id == DUDUNSPARCE:
                    my_active = next((p for p in my_state.active if p), None)
                    if my_active and my_active.id == DUNSPARCE:
                        score = 15000.0
                    else:
                        score = 13000.0
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
                    elif cid == SHAYMIN:
                        if bench_space >= 1:
                            score = 7000.0  # Bench protection
                        else:
                            score = -9999.0
                    elif cid == DUNSPARCE:
                        score = 5500.0 if dunsparce_field < 3 and bench_space > 0 else -9999.0
                    else:
                        score = 2000.0 if bench_space > 0 else -9999.0

                    # Early game: board development beats hand-holding.
                    # Push basics above supporters/trainers until bench is
                    # reasonably built out (fixes Dunsparce/Abra hoarding bug).
                    if early_game_undeveloped and score > -9000.0:
                        score += 4000.0

                # ── Trainer cards ────────────────────────────────────────────
                else:
                    # Calculate net hand size change to check if safe to play
                    net_change = -1 # Base cost: playing the card from hand
                    if cid in (POKE_PAD, NIGHT_STRETCH):
                        net_change = 0
                    elif cid in (HILDA, DAWN, LANAS_AID, RARE_CANDY):
                        net_change = 1 # Net positive
                    
                    if is_lethal:
                        my_active = next((p for p in my_state.active if p), None)
                        if my_active and my_active.id == ALAKAZAM:
                            current_hand_size = len(my_state.hand)
                            if (current_hand_size + net_change) * 20 < op_hp:
                                if cid not in (ENH_HAMMER, BOSS_ORDERS):
                                    score = -9999.0
                                    scores.append(score)
                                    continue

                    if cid == ENH_HAMMER:
                        # Remove opponent's special energy
                        op_active_has_special = any(
                            getattr(e, 'id', 0) not in (5, 2, 1, 3, 4, 6, 7, 8, 9)
                            for e in (getattr(op_active, 'energyCards', []) if op_active else [])
                        )
                        op_bench_has_special = any(
                            getattr(e, 'id', 0) not in (5, 2, 1, 3, 4, 6, 7, 8, 9)
                            for p in op_bench
                            for e in getattr(p, 'energyCards', [])
                        )
                        if mist_on_opponent:
                            score = 19000.0
                        elif op_active_has_special:
                            score = 8000.0
                        elif op_bench_has_special:
                            score = 5000.0
                        else:
                            score = -9999.0

                    elif cid == RARE_CANDY:
                        abra_in_play = field[ABRA] > 0
                        alakazam_in_hand = hand[ALAKAZAM] > 0
                        kadabra_missing = field[KADABRA] == 0
                        if abra_in_play and alakazam_in_hand and kadabra_missing:
                            score = 9800.0  # Skip Kadabra — instant Stage 2
                        else:
                            score = -9999.0

                    elif cid == POFFIN:
                        # Poffin searches for HP <= 70. Shaymin has 80 HP, so it CANNOT be searched by Poffin!
                        if bench_space >= 1:
                            score = 7500.0
                        else:
                            score = -9999.0
                        score += _deck_safety_discount(my_state.deckCount, 2)

                    elif cid == DAWN:
                        if not supporter_played:
                            clefairy_missing = field.get(LILLIE_CLEFAIRY_EX, 0) == 0 and hand.get(LILLIE_CLEFAIRY_EX, 0) == 0
                            if clefairy_missing and bench_space >= 1:
                                score = 9000.0  # Even higher — get Fairy Zone online ASAP
                            else:
                                score = 8500.0   # ALWAYS play Dawn — unconditional
                            score += _deck_safety_discount(my_state.deckCount, 3)
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
                            score += _deck_safety_discount(my_state.deckCount, 2)
                        else:
                            score = -9999.0


                    elif cid == BOSS_ORDERS:
                        if not supporter_played and op_bench:
                            # Calculate our active's damage
                            current_dmg = 0
                            my_active = next((p for p in my_state.active if p), None)
                            if my_active:
                                if my_active.id == ALAKAZAM:
                                    current_dmg = len(my_state.hand) * 20
                                elif my_active.id == LILLIE_CLEFAIRY_EX:
                                    my_bench = [p for p in my_state.bench if p]
                                    op_bench_list = [p for p in op_state.bench if p]
                                    current_dmg = 20 + 20 * (len(my_bench) + len(op_bench_list))
                                
                            best_target = max(op_bench, 
                                key=lambda p: _target_score(p, my_prizes, current_dmg))
                            best_score = _target_score(best_target, my_prizes, current_dmg)
                            active_score = _target_score(op_active, my_prizes, current_dmg) if op_active else 0
                            if best_score > active_score + 200:
                                if is_lethal and my_active and my_active.id in (ALAKAZAM, LILLIE_CLEFAIRY_EX):
                                    attack_opt = next((opt for opt in options if opt.type == OptionType.ATTACK), None)
                                    if attack_opt:
                                        current_attack_score = evaluate_attack(
                                            obs, attack_opt.index, op_hp, hand_size, my_prizes, len(op_state.prize), len(op_bench)
                                        )
                                        score = current_attack_score + 500.0
                                        print(f"[BOSS LETHAL OVERRIDE] attack_score={current_attack_score}, boss_score={score}")
                                    else:
                                        score = 7000.0
                                else:
                                    score = 7000.0
                            else:
                                score = -9999.0
                        else:
                            score = -9999.0

                    elif cid == LANAS_AID:
                        if not supporter_played:
                            hand_size = len(my_state.hand)
                            
                            # NEW: lethal-margin check — does recovering 3 cards flip a
                            # non-lethal Powerful Hand into a lethal one this turn?
                            op_hp = _hp_remaining(op_active) if op_active else 999
                            current_dmg = hand_size * 20
                            dmg_with_lana = (hand_size + 3) * 20
                            flips_to_lethal = current_dmg < op_hp <= dmg_with_lana
                            
                            if flips_to_lethal:
                                score = 15000.0  # highest priority — directly secures a KO
                                                   # that wasn't otherwise available this turn
                            else:
                                # NEW: weighted discard scoring instead of a single flat sum.
                                # High-value pieces (Alakazam line pieces that let us
                                # continue evolving/rebuilding, plus Lillie's Clefairy ex)
                                # count for more than generic energy.
                                high_value_in_discard = sum(
                                    discard[c] for c in [ABRA, KADABRA, ALAKAZAM, LILLIE_CLEFAIRY_EX]
                                )
                                low_value_in_discard = sum(
                                    discard[c] for c in [DUNSPARCE, DUDUNSPARCE, PSYCHIC_ENERGY]
                                )
                                
                                if hand_size <= 3 and (high_value_in_discard + low_value_in_discard) >= 2:
                                    score = 8500.0  # Emergency recovery after disruption, unchanged
                                elif high_value_in_discard >= 2:
                                    score = 7500.0  # NEW tier — pipeline rebuild is worth more
                                                      # than the old flat 6500 when it's genuinely
                                                      # high-value pieces, not just any 2 cards
                                elif high_value_in_discard >= 1 or low_value_in_discard >= 2:
                                    score = 6500.0
                                elif low_value_in_discard >= 1:
                                    score = 6000.0  # TigerGGG tactics — early usage, unchanged
                                else:
                                    score = -9999.0
                                    
                            # File-based logging for verification
                            try:
                                with open('lana_aid_log.txt', 'a') as f:
                                    high_val = high_value_in_discard if not flips_to_lethal else -1
                                    low_val = low_value_in_discard if not flips_to_lethal else -1
                                    f.write(f"LANA_AID: flips={flips_to_lethal}, high={high_val}, low={low_val}, hand={hand_size}, score={score}\n")
                            except:
                                pass

                        else:
                            score = -9999.0

                    elif cid == POKE_PAD:
                        # Search non-Rule Box Pokémon — finds Abra, Dunsparce
                        if alakazam_line_field < 2 or dunsparce_field < 1:
                            score = 6000.0
                        else:
                            score = 5000.0  # Just getting Dudunsparce is always good
                        score += _deck_safety_discount(my_state.deckCount, 1)

                    elif cid == NIGHT_STRETCH:
                        # Recover Pokémon from discard
                        alakazam_lost = discard[ALAKAZAM]
                        abra_lost = discard[ABRA]
                        shaymin_lost = discard[SHAYMIN]
                        has_shaymin = any(p and p.id == SHAYMIN for p in my_state.bench)
                        
                        if shaymin_lost >= 1 and not has_shaymin:
                            score = 7000.0
                        elif alakazam_lost >= 1:
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
                            score = 7000.0
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

                    elif cid == XEROSIC:
                        if not supporter_played:
                            opp_hand = op_state.handCount
                            if opp_hand > 3:
                                score = 8000.0  # Disrupt opponent's large hand
                            else:
                                score = -1000.0
                        else:
                            score = -9999.0

                    elif cid == NIGHTTIME_MINE:
                        current_stadium = getattr(state, 'stadium', None)
                        if current_stadium and getattr(current_stadium, 'playerIndex', my_idx) != my_idx:
                            score = 8000.0  # Replace opponent's stadium immediately
                        else:
                            score = 2500.0

                    elif cid == LILLIE_CLEFAIRY_EX:
                        # Only bench if facing Dragons
                        op_has_dragon = False
                        if op_active and getattr(op_active, 'pokemonType', -1) == 10:  # 10 is Dragon
                            op_has_dragon = True
                        for p in op_bench:
                            if getattr(p, 'pokemonType', -1) == 10:
                                op_has_dragon = True
                                
                        # Or if Dragapult is in the discard
                        if discard.get(121, 0) > 0 or any(p.id == 121 for p in (op_bench + [op_active]) if p):
                            op_has_dragon = True
                            
                        if op_has_dragon:
                            score = 9999.0
                        else:
                            score = -9999.0  # Dead card in non-Dragon matchups

                    else:
                        score = 1000.0

        # ── ATTACH ENERGY ────────────────────────────────────────────────────
        elif o.type == OptionType.ATTACH:
            if not energy_attached:
                card   = _get_card(obs, AreaType.HAND, o.index, my_idx)
                target = _get_card(obs, o.inPlayArea, o.inPlayIndex, my_idx)
                if card and target:
                    if card.id == ENRICHING_ENERGY:
                        if my_state.deckCount <= 4:
                            score = -9999.0  # Prevents drawing last 4 cards and instantly losing
                        elif post_disruption and target.id in (DUNSPARCE, DUDUNSPARCE):
                            score = 12000.0  # Highest priority when disrupted
                        elif target.id == DUNSPARCE:
                            score = 9500.0
                        elif target.id == DUDUNSPARCE:
                            score = 9000.0
                        else:
                            score = -9999.0
                    else:
                        energy_count = sum(1 for e in getattr(target, 'energyCards', []))
                        if energy_count >= 1:
                            # Alakazam only needs ONE energy to attack.
                            # We MUST NOT attach more than one because keeping extra energy
                            # in hand adds +20 damage to Powerful Hand!
                            if target.id in (ALAKAZAM, ALAKAZAM_TWM, KADABRA, ABRA):
                                score = -9999.0
                            elif target.id in (DUNSPARCE, DUDUNSPARCE):
                                score = -9999.0  # NEVER attach non-Enriching to Dunsparce line
                            else:
                                score = 100.0
                        else:
                            # Attach exactly one energy to power them up
                            if target.id in (DUNSPARCE, DUDUNSPARCE):
                                score = -9999.0  # NEVER attach non-Enriching to Dunsparce line
                            elif target.id == ALAKAZAM:
                                score = 9000.0
                            elif target.id == ALAKAZAM_TWM:
                                score = 8000.0
                            elif target.id == KADABRA:
                                score = 8000.0  # Pre-load backup attacker
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
            opponent_is_fighting = any(
                EnergyType.FIGHTING in getattr(p, 'energies', [])
                for p in [op_active] + list(op_bench)
                if p is not None
            )

            if active and active.id in (ALAKAZAM, ALAKAZAM_TWM) and opponent_is_fighting:
                score = -9999.0
            elif active and active.id in (DUNSPARCE, DUDUNSPARCE):
                # v3.32 Fix 1: Dunsparce/Dudunsparce is the designated tank.
                # The ONLY valid reason to retreat it is if an energized Alakazam
                # is ready to take over. Status conditions are NOT a valid reason
                # — Run Away Draw is the correct cure, not a plain retreat.
                alakazam_fully_ready = any(
                    p and p.id == ALAKAZAM and _energy_count(p) >= 1
                    for p in my_state.bench if p
                )
                score = 4000.0 if alakazam_fully_ready else -9999.0
            elif active and active.id not in (ALAKAZAM, ALAKAZAM_TWM):
                # Get Alakazam to active
                alakazam_ready = any(
                    p and p.id == ALAKAZAM and _energy_count(p) >= 1
                    for p in my_state.bench if p
                )
                base_score = 4000.0 if alakazam_ready else 500.0

                if my_status_curable_by_retreat:
                    base_score += 3000.0

                score = base_score

                # Wasteful early-game voluntary retreat guard (v3.42 Fix 1)
                # Only penalize if losing energy, undamaged, no status to cure, AND no Alakazam ready to take over
                if _energy_count(active) >= 1 and not my_status_curable_by_retreat and not alakazam_ready:
                    card_data = CARD_DB.get(active.id)
                    max_hp = getattr(card_data, 'hp', 999) if card_data else 999
                    if _hp_remaining(active) >= max_hp:
                        score = -9999.0  # Hard block: pure resource waste
                        try:
                            with open('retreat_block_log.txt', 'a') as f:
                                f.write(f"RETREAT BLOCKED: active={active.id}, energy={_energy_count(active)}, max_hp={max_hp}\n")
                        except:
                            pass
            else:
                score = -9999.0  # Never retreat Alakazam

        # ── END ─────────────────────────────────────────────────────────────
        elif o.type == OptionType.END:
            # End turn — but only if we've attacked or have nothing else to do
            score = -5000.0

        else:
            score = 0.0

        scores.append(score)


    scores = _sanity_check(obs, options, scores)
    

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
            
            if card and card.id == DUDUNSPARCE:
                if is_lethal:
                    score = -9999.0  # Don't draw if we're already lethal!
                else:
                    base_score = 9000.0
                    score = base_score + _deck_safety_discount(state.players[my_idx].deckCount, 3)
            elif card and card.id in (KADABRA, ALAKAZAM):
                # Psychic Draw activation
                base_score = 9000.0
                score = base_score + _deck_safety_discount(state.players[my_idx].deckCount, 2)
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
    op_idx = 1 - my_idx
    op_state = obs.current.players[op_idx]
    
    op_active = next((p for p in op_state.active if p), None)
    op_bench = [p for p in op_state.bench if p]
    
    op_is_fighting = False
    for p in [op_active] + op_bench:
        if p and (getattr(p, 'pokemonType', -1) == 6 or p.id in (678, 674)):
            op_is_fighting = True

    scores = []
    for o in options:
        card = _get_card(obs, AreaType.HAND, o.index, my_idx)
        if not card:
            scores.append(0.0)
            continue
        if card.id == DUNSPARCE:
            scores.append(100.0)
        elif card.id == ABRA:
            scores.append(50.0)
        elif card.id == ALAKAZAM:
            scores.append(80.0 if op_is_fighting else 10.0)
        elif card.id == DUDUNSPARCE: 
            scores.append(40.0)
        else:                        
            scores.append(10.0)
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
        area = getattr(o, 'area', AreaType.HAND)
        card = _get_card(obs, area, o.index, my_idx)
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
    return _pick_best(scores, min_count, max_count, allow_empty=True)


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
        elif cid == SHAYMIN:
            already_has_shaymin = any(p and p.id == SHAYMIN for p in state.players[my_idx].bench)
            score = 8500.0 if not already_has_shaymin else 1000.0
        elif cid == KADABRA:
            alakazam_line_missing = field[KADABRA] == 0 and field[ALAKAZAM] == 0
            if field[ABRA] >= 1 and alakazam_line_missing:
                score = 9700.0  # Beats Dudunsparce — evolving Abra is the immediate priority
            elif field[ABRA] >= 1:
                score = 8000.0
            else:
                score = 3000.0
        elif cid == ABRA:
            score = 7000.0 if alakazam_in_field < 3 else 1000.0
        elif cid == DUDUNSPARCE:
            if field[DUNSPARCE] >= 1:
                score = 9500.0
            else:
                score = 4000.0
        elif cid == DUNSPARCE:
            if field[DUNSPARCE] == 0:
                score = 9600.0
            elif field[DUNSPARCE] < 3:
                score = 5000.0
            else:
                score = 500.0
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

    return _pick_best(scores, min_count, max_count, allow_empty=True)


# ─────────────────────────────────────────────────────────────────────────────
# HANDLE TO DECK (context 9)
# ─────────────────────────────────────────────────────────────────────────────

def handle_to_deck(obs, options, min_count, max_count):
    """
    Choose which card(s) to shuffle from discard into the deck.
    Triggered by Sacred Ash / Super Rod.
    """
    print(f"[HANDLE TO DECK FIRED] options={len(options)} min={min_count} max={max_count}", flush=True)
    
    state  = obs.current
    my_idx = state.yourIndex
    field  = _field_counts(state, my_idx)

    alakazam_in_field = field[ABRA] + field[KADABRA] + field[ALAKAZAM]
    dudunsparce_in_field = field[DUNSPARCE] + field[DUDUNSPARCE]

    scores = []
    for o in options:
        if o.type == OptionType.NO:
            scores.append(-9999.0)
            continue
            
        card = _get_card(obs, o.area, o.index, my_idx)
        if not card:
            scores.append(0.0)
            continue

        cid = card.id
        score = 100.0

        if cid == DUDUNSPARCE:
            score = 10000.0 if dudunsparce_in_field < 2 else 5000.0
        elif cid == ALAKAZAM:
            score = 9000.0 if alakazam_in_field < 2 else 4500.0
        elif cid == KADABRA:
            score = 8000.0 if alakazam_in_field < 3 else 3000.0
        elif cid == ABRA:
            score = 7000.0 if alakazam_in_field < 3 else 1000.0
        elif cid == DUNSPARCE:
            score = 6000.0 if dudunsparce_in_field < 3 else 1000.0
        elif cid == LILLIE_CLEFAIRY_EX:
            score = 5000.0
        elif cid == SHAYMIN:
            score = 4000.0
        elif cid in (PSYCHIC_ENERGY, TELEPATH_ENERGY):
            score = 3000.0
        else:
            score = 2000.0  # Generic recovery

        scores.append(score)

    return _pick_best(scores, min_count, max_count, allow_empty=True)


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
    op_idx = 1 - my_idx
    op_state = state.players[op_idx]

    op_active = next((p for p in op_state.active if p), None)
    op_bench = [p for p in op_state.bench if p]
    
    op_is_fighting = False
    for p in [op_active] + op_bench:
        if p and (getattr(p, 'pokemonType', -1) == 6 or p.id in (678, 674)):
            op_is_fighting = True

    scores = []
    for o in options:
        poke = _get_card(obs, AreaType.BENCH, o.index, my_idx)
        if not poke:
            scores.append(0.0)
            continue

        energy = _energy_count(poke)
        hp_left = _hp_remaining(poke)

        if op_is_fighting:
            # Send up Alakazam to tank against Fighting due to Resistance
            if poke.id == ALAKAZAM:
                score = 15000.0 + energy * 500
            elif poke.id == ALAKAZAM_TWM:
                score = 14000.0 + energy * 300
            elif poke.id == ABRA:
                score = 2000.0
            elif poke.id == KADABRA:
                score = 1000.0
            elif poke.id in (DUNSPARCE, DUDUNSPARCE):
                score = 100.0  # Fighting-weak, explicitly deprioritize as a tank
            else:
                score = 300.0
        else:
            if poke.id == ALAKAZAM:
                score = 10000.0 + energy * 500  # Always prefer Alakazam
            elif poke.id == ALAKAZAM_TWM:
                score = 8000.0 + energy * 300
            elif poke.id == DUDUNSPARCE:
                score = 2500.0  # Better pivot (Ability)
            elif poke.id == DUNSPARCE:
                score = 2000.0  # Better pivot (0 Retreat)
            elif poke.id == KADABRA:
                score = 1000.0 + energy * 100
            elif poke.id == ABRA:
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
    """
    Score attaching this energy to this target.

    RULES:
    - Enriching Energy (13): ONLY attach to Dunsparce/Dudunsparce
      They shuffle back into deck = energy recycles. Draws 4 cards.
    - All other energy: ONLY attach to Alakazam line (Abra/Kadabra/Alakazam)
    - NEVER attach any energy to Dunsparce/Dudunsparce except Enriching
    - NEVER attach Enriching Energy to Alakazam line (waste of ACE SPEC)
    """
    state  = obs.current
    my_idx = state.yourIndex
    
    # Get the ID of the energy card being attached
    context_card = getattr(obs.select, 'contextCard', None)
    energy_id = getattr(context_card, 'id', 0) if context_card else 0

    scores = []
    for o in options:
        area  = o.inPlayArea if hasattr(o, 'inPlayArea') else AreaType.BENCH
        index = o.inPlayIndex if hasattr(o, 'inPlayIndex') else o.index
        poke  = _get_card(obs, area, index, my_idx)
        if not poke:
            scores.append(0.0)
            continue
            
        tid = poke.id
        score = 0.0

        if energy_id == ENRICHING_ENERGY:
            my_state = state.players[my_idx]
            if my_state.deckCount <= 4:
                score = -9999.0  # NEVER attach when deck is critically low
            elif tid == DUNSPARCE:
                score = 9500.0   # Best target — recycles + draws 4
            elif tid == DUDUNSPARCE:
                score = 9000.0   # Also recycles + draws 4
            else:
                score = -9999.0  # NEVER attach Enriching to Alakazam line

        elif energy_id == TELEPATH_ENERGY:
            my_state = state.players[my_idx]
            if my_state.deckCount <= 2:
                score = -9999.0  # Hard block
            elif tid in (ALAKAZAM, KADABRA, ABRA):
                if _energy_count(poke) == 0:
                    
                    score = 9500.0  # Best target — trigger ability
                else:
                    score = 8000.0
            else:
                score = -9999.0

        elif energy_id == PSYCHIC_ENERGY:
            if tid == DUNSPARCE or tid == DUDUNSPARCE:
                score = -9999.0  # NEVER attach to Dunsparce line
            elif tid == ALAKAZAM:
                if _energy_count(poke) >= 1:
                    score = 5000.0  # Cap at 1 (redirect to Kadabra)
                else:
                    score = 9000.0
            elif tid == KADABRA:
                score = 7000.0
            elif tid == ABRA:
                score = 4000.0
            elif tid == LILLIE_CLEFAIRY_EX:
                if area == AreaType.ACTIVE and _energy_count(poke) < 2:
                    score = 6000.0
                elif has_damage_blocker_revealed(state.players[1 - my_idx]) and _energy_count(poke) < 2:
                    score = 8000.0
                else:
                    score = -9999.0
            else:
                score = -9999.0
        else:
            score = -9999.0
            
        scores.append(score)

    return _pick_best(scores, min_count, max_count)


# ─────────────────────────────────────────────────────────────────────────────
# HANDLE EVOLVE (context 37)
# ─────────────────────────────────────────────────────────────────────────────

def handle_evolve(obs, options, min_count, max_count):
    state  = obs.current
    my_idx = state.yourIndex
    my_state = state.players[my_idx]

    my_status_afflicted = (
        getattr(my_state, 'asleep', False) or getattr(my_state, 'paralyzed', False)
        or getattr(my_state, 'confused', False) or getattr(my_state, 'poisoned', False)
        or getattr(my_state, 'burned', False)
    )

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

        if is_active and my_status_afflicted:
            score += 5000.0

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
    """Discard basic Psychic before special energy (or target opponent's Mist Energy)."""
    state = obs.current
    my_idx = state.yourIndex
    op_idx = 1 - my_idx
    
    my_active = next((p for p in state.players[my_idx].active if p), None)
    alakazam_is_or_will_be_attacker = (my_active is not None and my_active.id == ALAKAZAM)
    
    scores = []
    for o in options:
        # Default to old behavior if playerIndex is missing or points to us (fail-safe)
        if getattr(o, 'playerIndex', None) != op_idx:
            card = _get_card(obs, o.area if hasattr(o, 'area') else AreaType.ACTIVE,
                            o.index, my_idx)
            cid = getattr(card, 'id', 0) if card else 0
            if cid == PSYCHIC_ENERGY:
                scores.append(900.0)   # Discard basic first
            elif cid == TELEPATH_ENERGY:
                scores.append(700.0)
            elif cid == ENRICHING_ENERGY:
                scores.append(100.0)   # Keep ACE SPEC as long as possible
            else:
                scores.append(500.0)
        else:
            # New behavior: Target opponent's energy (e.g., via Enhanced Hammer)
            # Find the targeted Pokémon
            target_pokemon = None
            try:
                op_state = state.players[op_idx]
                area = o.area if hasattr(o, 'area') else AreaType.ACTIVE
                idx = o.index if hasattr(o, 'index') and o.index is not None else 0
                if area == AreaType.ACTIVE:
                    target_pokemon = op_state.active[idx] if idx < len(op_state.active) else None
                elif area == AreaType.BENCH:
                    target_pokemon = op_state.bench[idx] if idx < len(op_state.bench) else None
            except Exception:
                pass
            
            # Find the targeted energy card
            energy_card = None
            if target_pokemon and hasattr(o, 'energyIndex') and o.energyIndex is not None:
                try:
                    energy_card = target_pokemon.energyCards[o.energyIndex]
                except (IndexError, AttributeError):
                    pass
            
            energy_id = getattr(energy_card, 'id', None)
            is_opponent_active = (target_pokemon is not None and target_pokemon in state.players[op_idx].active)
            
            if energy_id == MIST_ENERGY:
                if alakazam_is_or_will_be_attacker and is_opponent_active:
                    scores.append(9800.0)
                else:
                    scores.append(7000.0)
            else:
                scores.append(3000.0)
                
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


# ─────────────────────────────────────────────────────────────────────────────
# SANITY CHECK — catch catastrophic mistakes before they execute
# These are game-losing moves no human player would ever make
# ─────────────────────────────────────────────────────────────────────────────

def _sanity_check(obs, options, scores):
    """
    Override scores for any move that would instantly lose the game.
    Called at the end of handle_main before returning.
    """
    state  = obs.current
    my_idx = state.yourIndex
    my_state = state.players[my_idx]

    bench = [p for p in my_state.bench if p is not None]
    bench_count = len(bench)

    for i, o in enumerate(options):
        # RULE 1: Never use Teleporter with empty bench
        if o.type == OptionType.ABILITY:
            if bench_count == 0:
                scores[i] = -9999.0  # Instant loss prevention

        # RULE 2: Never end turn if we can attack
        if o.type == OptionType.END:
            has_attack = any(opt.type == OptionType.ATTACK
                           for opt in options)
            if has_attack:
                scores[i] = -9999.0  # Never pass when we can attack

        # RULE 3: Never use Run Away Draw if it would empty the board
        # (Dudunsparce shuffles itself back — safe unless it's the only Pokemon)
        if o.type == OptionType.ABILITY:
            active = my_state.active[0] if my_state.active else None
            if (active and active.id == DUDUNSPARCE and
                bench_count == 0):
                scores[i] = -9999.0  # Would leave board empty

    return scores
