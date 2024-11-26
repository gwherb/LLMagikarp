from icecream import ic
from .utils import *
from .type_effectiveness import *

historical_turn_2 = None

def opposition_state_gen(battle, model):
    """
    Format battle observations into a structured prompt for decision making.
    
    Args:
        battle_obs: Dictionary containing battle observations
    
    Returns:
        str: Formatted prompt string
    """
    # Get the most recent observation (highest key number)
    battle_obs = battle.observations
    current_turn = max(battle_obs.keys())
    obs = battle_obs[current_turn]
    
    prompt_parts = []
    
    # Format battle header
    prompt_parts.append(f"BATTLE STATE - TURN {current_turn + 1}")
    prompt_parts.append("============================\n")

    # Format historical turns
    global historical_turn_2
    if historical_turn_2 and current_turn > 0:
        prompt_parts.append(f"PREVIOUS TURN ({current_turn - 1}):")
        prompt_parts.append(historical_turn_2)
        prompt_parts.append("")
    
    historical_turn_1 = get_last_turn_observation(obs.events, model)
    prompt_parts.append(f"LAST TURN ({current_turn}):")
    prompt_parts.append(historical_turn_1)
    prompt_parts.append("")
    historical_turn_2 = historical_turn_1
    
    
    # Current turn information
    prompt_parts.append(f"Turn {current_turn + 1} (Current turn):")

    
    # Opponent Pokemon information
    # Get the number of Pokemon the opponent has left
    opponent_team_count = 6
    opponents_observed_team = [pokemon for pokemon in battle.opponent_team.values() if not pokemon.fainted]
    fainted = len([
        pokemon for pokemon in battle.opponent_team.values() if pokemon.fainted
    ])

    # Format opponent section
    prompt_parts.append("OPPONENT STATUS")
    prompt_parts.append("--------------")
    prompt_parts.append(f"Remaining Pokemon: {opponent_team_count - fainted}/6\n")

    # Get the opponent's active Pokemon
    opponent_active_pokemon = battle.opponent_active_pokemon

    # Get defensive type info for the opponent's active Pokemon
    type_1 = opponent_active_pokemon.type_1.name
    type_2 = opponent_active_pokemon.type_2.name if opponent_active_pokemon.type_2 else None
    def_matchup = defensive_type_matchup([type_1, type_2])
    def_prompt = load_prompt("defensive_type_effectiveness.txt")
    def_prompt = def_prompt.format(
        Species=opponent_active_pokemon.species,
        Type1=type_1,
        Type2=type_2,
        m4x=", ".join(def_matchup['4x']) if def_matchup['4x'] else "NONE",
        m2x=", ".join(def_matchup['2x']) if def_matchup['2x'] else "NONE",
        m1x=", ".join(def_matchup['1x']) if def_matchup['1x'] else "NONE",
        m0_5x=", ".join(def_matchup['0.5x']) if def_matchup['0.5x'] else "NONE",
        m0_25x=", ".join(def_matchup['0.25x']) if def_matchup['0.25x'] else "NONE",
        m0x=", ".join(def_matchup['0x']) if def_matchup['0x'] else "NONE",
    )
    off_m1, off_m2 = offensive_type_matchup([type_1, type_2])
    off_prompt = None
    if off_m2:
        off_prompt = load_prompt("offensive_two_type_effectiveness.txt")
        off_prompt = off_prompt.format(
            Species=opponent_active_pokemon.species,
            Type1=type_1,
            Type2=type_2,
            supereffective1=", ".join(off_m1['2x']) if off_m1['2x'] else "NONE",
            resisted1=", ".join(off_m1['0.5x']) if off_m1['0.5x'] else "NONE",
            immune1=", ".join(off_m1['0x']) if off_m1['0x'] else "NONE",
            supereffective2=", ".join(off_m2['2x']) if off_m2['2x'] else "NONE",
            resisted2=", ".join(off_m2['0.5x']) if off_m2['0.5x'] else "NONE",
            immune2=", ".join(off_m2['0x']) if off_m2['0x'] else "NONE",
        )
    else:
        off_prompt = load_prompt("offensive_one_type_effectiveness.txt")
        off_prompt = off_prompt.format(
            Species=opponent_active_pokemon.species,
            Type=type_1,
            supereffective=", ".join(off_m1['2x']) if off_m1['2x'] else "NONE",
            resisted=", ".join(off_m1['0.5x']) if off_m1['0.5x'] else "NONE",
            immune=", ".join(off_m1['0x']) if off_m1['0x'] else "NONE",
        )

    # Format active opponent Pokemon
    prompt_parts.append(f"ACTIVE POKEMON: {opponent_active_pokemon.species}")
    prompt_parts.append(f"HP: {opponent_active_pokemon.current_hp_fraction * 100:.0f}%")
    prompt_parts.append(f"Status: {opponent_active_pokemon.status}")
    prompt_parts.append(f"Ability: {opponent_active_pokemon.ability if opponent_active_pokemon.ability else 'Unknown'}")
    prompt_parts.append(f"Type: {opponent_active_pokemon.type_1.name}/{opponent_active_pokemon.type_2.name if opponent_active_pokemon.type_2 else 'None'}\n")
    
    stats = estimate_stats(opponent_active_pokemon)
    if stats:
        prompt_parts.append(f"Estimated Stats: Attack - {stats['attack']}, Defense - {stats['defense']}, Special Attack - {stats['special-attack']}, Special Defense - {stats['special-defense']}, Speed - {stats['speed_low']} to {stats['speed_high']}\n")
    
    # Add type analysis sections
    prompt_parts.append("[DEFENSIVE ANALYSIS]")
    prompt_parts.append(def_prompt)
    prompt_parts.append("")
    prompt_parts.append("[OFFENSIVE ANALYSIS]")
    prompt_parts.append(off_prompt)
    prompt_parts.append("")

    # Player Pokemon information
    player_active_pokemon = battle.active_pokemon

    # Format your Pokemon section
    prompt_parts.append("YOUR STATUS")
    prompt_parts.append("----------")
    prompt_parts.append(f"ACTIVE POKEMON: {player_active_pokemon.species}")
    prompt_parts.append(f"HP: {player_active_pokemon.current_hp_fraction * 100:.0f}%")
    prompt_parts.append(f"Status: {player_active_pokemon.status}")
    prompt_parts.append(f"Ability: {player_active_pokemon.ability}")
    prompt_parts.append(f"Type: {player_active_pokemon.type_1.name}/{player_active_pokemon.type_2.name if player_active_pokemon.type_2 else 'None'}\n")
    prompt_parts.append(f"Stats: Attack - {player_active_pokemon.stats['atk']}, Defense - {player_active_pokemon.stats['def']}, Special Attack - {player_active_pokemon.stats['spa']}, Special Defense - {player_active_pokemon.stats['spd']}, Speed - {player_active_pokemon.stats['spe']}\n")
    
    # Format moves
    available_moves = player_active_pokemon.moves
    prompt_parts.append("AVAILABLE MOVES:")
    for move in available_moves:
        prompt_parts.append(
            f"- {move}: {available_moves[move].type.name} | "
            f"Power: {available_moves[move].base_power} | "
            f"Category: {available_moves[move].category.name} | "
            f"Priority: {available_moves[move].priority} | "
            f"Effect: {available_moves[move].secondary}"
        )
    prompt_parts.append("")
    
    # Format switches section
    if battle.available_switches:
        prompt_parts.append("AVAILABLE SWITCHES:")
        for pokemon in battle.available_switches:
            prompt_parts.append(
                f"- {pokemon.species} ({pokemon.current_hp_fraction * 100:.0f}% HP) | "
                f"Status: {pokemon.status} | "
                f"Ability: {pokemon.ability} | "
                f"Type: {pokemon.type_1.name}/{pokemon.type_2.name if pokemon.type_2 else 'None'} | "
                f"Stats: Attack - {pokemon.stats['atk']}, Defense - {pokemon.stats['def']}, Special Attack - {pokemon.stats['spa']}, Special Defense - {pokemon.stats['spd']}, Speed - {pokemon.stats['spe']}"
            )
            prompt_parts.append("  Moves:")
            for move in pokemon.moves:
                prompt_parts.append(
                    f"  * {move}: {pokemon.moves[move].type.name} | "
                    f"Power: {pokemon.moves[move].base_power} | "
                    f"Category: {pokemon.moves[move].category.name}"
                )
            prompt_parts.append("")
    else:
        prompt_parts.append("AVAILABLE SWITCHES: None\n")

    return "\n".join(prompt_parts)