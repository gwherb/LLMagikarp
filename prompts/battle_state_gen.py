from openai import OpenAI
import os
from icecream import ic
from dotenv import load_dotenv, find_dotenv
from .utils import load_prompt
from .type_effectiveness import *

historical_turn_2 = None

def format_battle_prompt(battle, model):
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
    if historical_turn_2:
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
        prompt_parts.append(f"Estimated Stats: Attack - {stats['attack']}, Defense - {stats['defense']}, Special Attack - {stats['special-attack']}, Special Defense - {stats['special-defense']}, Speed - {stats['speed']}\n")
    
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

# Use LLM convert last turn into a portion of a prompt
def get_last_turn_observation(events, model):
    """
    Creates a prompt for an LLM to translate Pokemon battle events into natural language.
    
    Args:
        events: List of battle events from the last turn
        
    Returns:
        str: Natural language description of the events
    """
    # Initialize the OpenAI client
    # Get the absolute path to your .env file
    load_dotenv(find_dotenv())
    client = OpenAI(
        api_key=os.getenv("OPENAI_API_KEY")
    )

    # Convert events list into a more readable format
    formatted_events = []
    unwanted_events = ['init', 'title', 'gametype', 'player', 'teamsize', 'gen', 'tier', 'rule', 'j', 'upkeep']
    for event in events:
        if event[1] not in unwanted_events:
            formatted_events.append(' '.join(event[1:]))
    
    events_text = '\n'.join(formatted_events)
    
    # Create a prompt for the LLM
    system_message = load_prompt("battle_state_gen_system.txt")
    user_message = load_prompt("battle_state_gen_user.txt")

    user_message = user_message.format(events_text=events_text)

    try:
        # Make the API call using the new format
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message}
            ],
            temperature=1,
            max_tokens=150
        )
        
        # Extract the response text (new format)
        return response.choices[0].message.content.strip()
        
    except Exception as e:
        print(f"Error calling ChatGPT API: {e}")
        return f"Last turn events: {events_text}"

def estimate_stats(pokemon) -> dict[str, int]:
    if not pokemon or not pokemon.base_stats:
        return None
    
    # Constants for calculation
    level = pokemon.level  # Level 100 Pokemon
    iv = 32  # Maximum IVs
    ev_invested = 252  # Maximum EVs for invested stats
    ev_uninvested = 0  # No EVs for uninvested stats
    
    def calculate_stat(base: int, level: int, iv: int, ev: int, nature: float = 1.0) -> int:
        return (((2 * base + iv + (ev // 4)) * level // 100) + 5) * nature
    
    # Get relevant base stats (excluding HP)
    stats_list = [
        ("attack", pokemon.base_stats["atk"]),
        ("defense", pokemon.base_stats["def"]),
        ("special-attack", pokemon.base_stats["spa"]),
        ("special-defense", pokemon.base_stats["spd"]),
        ("speed", pokemon.base_stats["spe"])
    ]
    
    # Sort stats by base value to determine likely EV investment
    sorted_stats = sorted(stats_list, key=lambda x: x[1], reverse=True)
    primary_stat = sorted_stats[0][0]
    # Secondary stat is always speed stat to maximize speed control
    secondary_stat = "speed"
    
    # Calculate stats
    stats = {}
    for stat_name, base_value in stats_list:
        ev = ev_invested if stat_name in (primary_stat, secondary_stat) else ev_uninvested
        nature = 1.0
        if stat_name == "speed":
            nature = 1.1 if primary_stat == "speed" else 1.0
        stats[stat_name] = calculate_stat(base_value, level, iv, ev, nature=nature)
    
    return stats

def test_historic_prompt():
    # Test the function
    events=[['',
            'move',
            'p2a: Kleavor',
            'Close Combat',
            'p1a: Swalot'],
            ['', '-resisted', 'p1a: Swalot'],
            ['', '-damage', 'p1a: Swalot', '58/100'],
            ['', '-unboost', 'p2a: Kleavor', 'def', '1'],
            ['', '-unboost', 'p2a: Kleavor', 'spd', '1'],
            ['',
            'move',
            'p1a: Swalot',
            'Earthquake',
            'p2a: Kleavor'],
            ['', '-damage', 'p2a: Kleavor', '127/237'],
            ['',
            '-heal',
            'p1a: Swalot',
            '64/100',
            '[from] item: Leftovers'],
            ['', 'upkeep'],
            ['', 'turn', '15']]
    # ic(get_last_turn_observation(events))  # Should return a natural language summary

if __name__ == "__main__":
    test_historic_prompt()
    # Test the function
    # from poke_env.player.random_player import RandomPlayer
    # random_player = RandomPlayer()