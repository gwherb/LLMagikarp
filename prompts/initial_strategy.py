from openai import OpenAI
from dotenv import load_dotenv, find_dotenv
from icecream import ic
import json
from .utils import load_prompt

def get_strategy(battle_state, model='gpt-4o'):

    # Parse battle state to only look at own team:
    team_description = battle_state.split("YOUR STATUS\n----------")[1]
    
    system_message = load_prompt("strategy_system.txt")
    user_message = load_prompt("strategy_user.txt")
    user_message = user_message.format(team_description=team_description)

    prompt = {
        "system": system_message,
        "human": user_message,
    }

    load_dotenv(find_dotenv())
    client = OpenAI()
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": prompt["system"]},
            {"role": "user", "content": prompt["human"]}
        ],
        temperature=1
    )

    return response.choices[0].message['content']
