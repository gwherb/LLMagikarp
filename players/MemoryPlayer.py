from icecream import ic
from prompts import *
from players import LoggingPlayer
from statistics import multimode

class MemoryPlayer(LoggingPlayer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.last_thought = None

    def choose_move(self, battle):
            # Get battle state and decision
            battle_state = memory_battle_state(battle, self.LLM_model, thought=self.last_thought)
            # ic(battle_state) # Debugging
            thought, action_type, action_name = move_prompt(battle_state, self.LLM_model, mode="memory")
            self.last_thought = thought

            # Log the turn
            if self._game_started:  # Only log if game is properly started
                self._battle_logger.log_turn(
                    turn_number=battle.turn,
                    battle_state=battle_state,
                    thought=thought,
                    action_type=action_type,
                    action_name=action_name,
                    is_random=False
                )
            
            # Execute move logic
            if action_type == "move":
                for move in battle.available_moves:
                    if move.id == action_name:
                        return self.create_order(move)
            elif action_type == "switch":
                for switch in battle.available_switches:
                    if switch.species == action_name:
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