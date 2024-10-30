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

    async def battle_against(self, opponent, n_battles=1):
        """Override battle_against to add logging for local battles."""
        if not self._game_started:
            self._battle_logger.start_new_game("local")
            self._game_started = True
        
        await super().battle_against(opponent, n_battles)
        
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
            
        self._battle_logger.end_game(outcome)
        self._game_started = False

    async def ladder(self, n_games):
        """Override ladder to add logging for ladder battles."""
        if not self._game_started:
            self._battle_logger.start_new_game("ladder")
            self._game_started = True
        
        await super().ladder(n_games)
        
        # Log the outcome with final rank
        self._battle_logger.end_game(
            outcome="completed",
            final_rank=self.rating
        )
        self._game_started = False

    def choose_move(self, battle):
        """Override choose_move to add logging for each turn."""
        # Get battle state and decision
        battle_state = format_battle_prompt(battle)
        thought, action_type, action_name = move_prompt(battle_state)
        
        # Log the turn
        self._battle_logger.log_turn(
            turn_number=battle.turn,
            battle_state=battle_state,
            thought=thought,
            action_type=action_type,
            action_name=action_name
        )
        
        # Execute the move logic
        if action_type == "move":
            for move in battle.available_moves:
                if move.id == action_name:
                    return self.create_order(move)
        elif action_type == "switch":
            for switch in battle.available_switches:
                if switch.species == action_name:
                    return self.create_order(switch)
        
        return self.choose_random_move(battle)