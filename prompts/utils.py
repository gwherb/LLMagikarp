from pathlib import Path
import os
from dotenv import load_dotenv, find_dotenv
from openai import OpenAI

def load_prompt(filename):
    prompt_path = Path("prompts") / filename
    with open(prompt_path, "r", encoding="utf-8") as f:
        return f.read().strip()
    
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
    level = pokemon.level
    iv = 31  # Maximum IVs
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
        ("speed_high", pokemon.base_stats["spe"]),
        ("speed_low", pokemon.base_stats["spe"])
    ]
    
    # Sort stats by base value to determine likely EV investment
    sorted_stats = sorted(stats_list, key=lambda x: x[1], reverse=True)
    primary_stat = sorted_stats[0][0]
    # Secondary stat is always speed stat to maximize speed control
    secondary_stat = "speed_high" if sorted_stats[0][0] != "speed_high" else sorted_stats[2][0]
    
    # Calculate stats
    stats = {}
    for stat_name, base_value in stats_list:
        ev = ev_invested if stat_name in (primary_stat, secondary_stat) else ev_uninvested
        nature = 1.0
        if stat_name == "speed_high":
            nature = 1.1 if primary_stat == "speed_high" or primary_stat == "speed_low" else 1.0
        stats[stat_name] = calculate_stat(base_value, level, iv, ev, nature=nature)
    
    return stats