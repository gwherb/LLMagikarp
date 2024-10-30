from poke_env import Player
from icecream import ic
from prompts import *

class TestPlayer(Player):

    move_counter = 0

    def choose_move(self, battle):

        # For incremental testing at only one turn:
        # # ic(battle._current_observation)
        # if self.move_counter == 1:
        #     prompt = format_battle_prompt(battle)
        #     ic(self.move_counter)
        #     ic(prompt)
        #     # ic(len(battle.observations))
        # self.move_counter += 1

        # Get prompt for decision making
        battle_state = format_battle_prompt(battle)

        # use prompt to make decision:
        thought, move_type, action_name = move_prompt(battle_state)
        ic(battle_state)
        ic(battle.turn)
        ic(move_type)
        ic(action_name)


        # Select move depending on the prompt
        if move_type == "move":
            # Select move
            for move in battle.available_moves:
                if move.id == action_name:
                    return self.create_order(move)

        elif move_type == "switch":
            # Select switch
            for switch in battle.available_switches:
                if switch.species == action_name:
                    return self.create_order(switch)

        # Not sure what to do?
        ic("Random move")
        return self.choose_random_move(battle)