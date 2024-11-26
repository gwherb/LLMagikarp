from openai import OpenAI
from dotenv import load_dotenv, find_dotenv
from icecream import ic
import json
from .utils import load_prompt

def move_prompt(battle_state, model, mode=None):
    
    system_message = load_prompt("move_gen_system.txt")

    if mode == "memory":
        user_message = load_prompt("memory_move_gen.txt")
    elif mode == "opposition":
        user_message = load_prompt("opposition_move_prompt.txt")
        system_message = load_prompt("opposition_system.txt")
    else:
        user_message = load_prompt("move_gen_user_3shot.txt")

    user_message = user_message.format(battle_state=battle_state)

    prompt = {
        "system": system_message,
        "human": user_message,
        "function_schema": {
            "name": "select_move",
            "description": "Select a move or switch action in Pokemon Showdown battle",
            "parameters": {
                "type": "object",
                "properties": {
                    "Thought": {
                        "type": "string",
                        "description": "Strategic reasoning behind the selected action"
                    },
                    "action_type": {
                        "type": "string",
                        "enum": ["move", "switch"],
                        "description": "Type of action to take: 'move' for using a move, 'switch' for switching Pokemon"
                    },
                    "action_name": {
                        "type": "string",
                        "description": "Name of the move to use or Pokemon to switch to, in lowercase",
                        "pattern": "^[a-z]+$"
                    }
                },
                "required": ["Thought", "action_type", "action_name"]
            }
        }
    }

    load_dotenv(find_dotenv())
    client = OpenAI()
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": prompt["system"]},
            {"role": "user", "content": prompt["human"]}
        ],
        functions=[prompt["function_schema"]],
        function_call={"name": "select_move"},
        temperature=1
    )


    # Extract the function call arguments from the response
    function_args = json.loads(response.choices[0].message.function_call.arguments)
    
    # Return the three specific fields
    # ic(function_args)
    
    # Fix for when actions are not properly generated:
    if 'action_type' not in function_args:
        function_args['action_type'] = None

    if 'action_name' not in function_args:
        function_args['action_name'] = None

    return (
        function_args["Thought"],
        function_args["action_type"],
        function_args["action_name"]
    )

def test_move_prompt():
    battle_state = '''Turn 1 (Last turn):'
             'Cyclizar was switched in at full HP. Carbink used Iron Defense on itself, '
             'boosting its Defense by 2 stages. No damage was dealt during this turn.
            '
             'Turn 2 (Current turn):
            '
             'Opponent has 6 Pokemon left.
            '
             "Opponent's active Pokemon: carbink (100% HP), Status: None, Ability: "
             'Unknown, Type 1: FIGHTING Type 2: None
            '
             'Your active Pokemon: cyclizar (100% HP), Status: None, Ability: regenerator, '
             'Type 1: DRAGON Type 2: NORMAL
            '
             'Your active Pokemon has the following moves:
            '
             'Move: shedtail, Base Power: 0, Type: NORMAL, Category: STATUS
            '
             'Move: knockoff, Base Power: 65, Type: DARK, Category: PHYSICAL
            '
             'Move: rapidspin, Base Power: 50, Type: NORMAL, Category: PHYSICAL
            '
             'Move: dracometeor, Base Power: 130, Type: DRAGON, Category: SPECIAL
            '
             'Your available Pokemon:
            '
             'Available Switch: kleavor (100% HP), Status: None, Ability: sharpness, Type '
             '1: BUG Type 2: ROCK
            '
             'Available Switch: pyroar (100% HP), Status: None, Ability: unnerve, Type 1: '
             'FIRE Type 2: NORMAL
            '
             'Available Switch: lanturn (100% HP), Status: None, Ability: voltabsorb, Type '
             '1: WATER Type 2: ELECTRIC
            '
             'Available Switch: jumpluff (100% HP), Status: None, Ability: infiltrator, '
             'Type 1: GRASS Type 2: FLYING
            '
             'Available Switch: dugtrio (100% HP), Status: None, Ability: arenatrap, Type '
             '1: GROUND Type 2: None'''
    # ic(move_prompt(battle_state))

if __name__ == "__main__":
    test_move_prompt()