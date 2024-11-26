from icecream import ic
from prompts import *
from players import LoggingPlayer
from statistics import multimode

class SC3Player(LoggingPlayer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.LLM_model = 'gpt-4o'

    def choose_move(self, battle):
        """Override choose_move to add logging for each turn."""
        # Get battle state and decision
        battle_state = format_battle_prompt(battle, self.LLM_model)

        actions = []
        for i in range(3):
            thought, action_type, action_name = move_prompt(battle_state, self.LLM_model)
            actions.append((thought, action_type, action_name))
        
        # Get the most common action_name (index 2)
        action_names = [action[2] for action in actions]
        voting = multimode(action_names)
        most_common_name = voting[0]
        consensus = True if len(voting) < 3 else False
        # Find the first full action tuple that matches the most common name
        most_common_action = next(action for action in actions if action[2] == most_common_name)

        # Log the turn
        if self._game_started:  # Only log if game is properly started
            self._battle_logger.log_turn(
                turn_number=battle.turn,
                battle_state=battle_state,
                thought=most_common_action[0],
                action_type=most_common_action[1],
                action_name=most_common_action[2],
                is_random=False,
                consensus=consensus,
                voting=voting
            )
        
        # Execute move logic
        if most_common_action[1] == "move":
            for move in battle.available_moves:
                if move.id == most_common_action[2]:
                    return self.create_order(move)
        elif most_common_action[1] == "switch":
            for switch in battle.available_switches:
                if switch.species == most_common_action[2]:
                    return self.create_order(switch)
        
        # If we get here, we need to make a random move
        random_move = self.choose_random_move(battle)
        
        # Log the random move
        if self._game_started:
            self._battle_logger.log_turn(
                turn_number=battle.turn,
                battle_state=battle_state,
                thought=thought,
                action_type=action_type,
                action_name=action_name,
                is_random=True
            )
        
        return random_move