from poke_env import Player
from icecream import ic
from prompts import *
from battle_logger import BattleLogger

class LoggingPlayer(Player):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._battle_logger = BattleLogger()
        self._game_started = False
        self._current_battle = None
        self.LLM_model = 'gpt-4o-mini'

    async def battle_against(self, opponent, n_battles=1):
        """Override battle_against to add logging for local battles."""
        # Store the original n_battles
        total_battles = n_battles
        
        # Run each battle separately to ensure proper logging
        for battle_number in range(total_battles):
            # Reset game state for new battle
            self._game_started = False
            
            # Start new battle log
            if not self._game_started:
                self._battle_logger = BattleLogger()  # Create new logger for each battle
                self._battle_logger.start_new_game("local", self.LLM_model)
                self._game_started = True
            
            # Run single battle
            await super().battle_against(opponent, n_battles=1)
            
            # Get the battle outcome from the most recent battle
            if len(self._battles) > 0:
                battle = list(self._battles.values())[-1]
                won = battle.won
                if won is not None:
                    outcome = "win" if won else "loss"
                else:
                    outcome = "draw"
            else:
                outcome = "unknown"
                
            # End the current battle log
            self._battle_logger.end_game(outcome)
            self._game_started = False
            
            # Clear any remaining battle state
            self._current_battle = None
            self._battles.clear()  # Clear battles dictionary after logging

    def choose_move(self, battle):
        """Override choose_move to add logging for each turn."""
        # Get battle state and decision
        battle_state = format_battle_prompt(battle, self.LLM_model)
        thought, action_type, action_name = move_prompt(battle_state, self.LLM_model)
        ic(battle_state)

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