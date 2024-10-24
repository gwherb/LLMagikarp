from openai import OpenAI
import os
from icecream import ic
from dotenv import load_dotenv, find_dotenv
from .move_prompt import load_prompt

def format_battle_prompt(battle):
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
    
    # Format historical turns from events
    historical_turns = get_last_turn_observation(obs.events)
    prompt_parts.append(f"Turn {current_turn} (Last turn):")
    prompt_parts.append(historical_turns)
    
    # Current turn information
    prompt_parts.append(f"Turn {current_turn + 1} (Current turn):")
    
    # Opponent Pokemon information
    # Get the number of Pokemon the opponent has left
    opponent_team_count = 6
    opponents_observed_team = [pokemon for pokemon in battle.opponent_team.values() if not pokemon.fainted]
    fainted = len([
        pokemon for pokemon in battle.opponent_team.values() if pokemon.fainted
    ])

    # Get the opponent's active Pokemon
    opponent_active_pokemon = battle.opponent_active_pokemon

    # Format opponent Pokemon information
    prompt_parts.append(f"Opponent has {opponent_team_count - fainted} Pokemon left.")
    prompt_parts.append(f"Opponent's active Pokemon: {opponent_active_pokemon.species} ({opponent_active_pokemon.current_hp_fraction * 100:.0f}% HP), Status: {opponent_active_pokemon.status}, Ability: {opponent_active_pokemon.ability if opponent_active_pokemon.ability else 'Unknown'}, Type 1: {opponent_active_pokemon.type_1.name} Type 2: {opponent_active_pokemon.type_2.name if opponent_active_pokemon.type_2 else 'None'}")
    for pokemon in opponents_observed_team:
        if pokemon.species != opponent_active_pokemon.species:
            prompt_parts.append(f"Opponent's available swtich: {pokemon.species} ({pokemon.current_hp_fraction * 100:.0f}% HP)")

    # Player Pokemon information
    # Get the player's active Pokemon
    player_active_pokemon = battle.active_pokemon

    # Format player Pokemon information
    prompt_parts.append(f"Your active Pokemon: {player_active_pokemon.species} ({player_active_pokemon.current_hp_fraction * 100:.0f}% HP), Status: {player_active_pokemon.status}, Ability: {player_active_pokemon.ability}, Type 1: {player_active_pokemon.type_1.name} Type 2: {player_active_pokemon.type_2.name if player_active_pokemon.type_2 else 'None'}")
    prompt_parts.append(f"Your active Pokemon has the following moves:")
    available_moves = player_active_pokemon.moves
    for move in available_moves:
        name = move
        move_obj = available_moves[move]
        prompt_parts.append(f"Move: {name}, Base Power: {move_obj.base_power}, Type: {move_obj.type.name}, Category: {move_obj.category.name}")
    prompt_parts.append(f"Your available Pokemon:")
    for pokemon in battle.available_switches:
        prompt_parts.append(f"Available Switch: {pokemon.species} ({pokemon.current_hp_fraction * 100:.0f}% HP), Status: {pokemon.status}, Ability: {pokemon.ability}, Type 1: {pokemon.type_1.name} Type 2: {pokemon.type_2.name if pokemon.type_2 else 'None'}")
    
    return "\n".join(prompt_parts)

# Use LLM convert last turn into a portion of a prompt
def get_last_turn_observation(events):
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
            model="gpt-4o-mini",
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
    ic(get_last_turn_observation(events))  # Should return a natural language summary

if __name__ == "__main__":
    test_historic_prompt()
    # Test the function
    # from poke_env.player.random_player import RandomPlayer
    # random_player = RandomPlayer()