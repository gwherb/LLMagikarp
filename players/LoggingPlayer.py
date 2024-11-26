import asyncio
from poke_env import Player
from icecream import ic
from prompts import *
from battle_logger import BattleLogger
from time import perf_counter

class LoggingPlayer(Player):
    def __init__(self, model='gpt-4o-mini', *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._battle_logger = BattleLogger()
        self._game_started = False
        self._current_battle = None
        self.LLM_model = model

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
            ic(f"Game {battle_number + 1}/{total_battles} complete. Outcome: {outcome}")
            
            # Clear any remaining battle state
            self._current_battle = None
            self._battles.clear()  # Clear battles dictionary after logging

    async def _ladder(self, n_games: int):
        """Override _ladder to add logging for ladder battles."""
        await self.ps_client.logged_in.wait()
        start_time = perf_counter()
        completed_games = 0

        while completed_games < n_games:
            # Reset game state for new battle
            self._game_started = False
            
            # Start new battle log before searching for game
            if not self._game_started:
                self._battle_logger = BattleLogger()
                self._battle_logger.start_new_game("ladder", self.LLM_model)
                self._game_started = True
                ic(f"Starting ladder game {completed_games + 1}/{n_games}")

            async with self._battle_start_condition:
                await self.ps_client.search_ladder_game(self._format, self.next_team)
                await self._battle_start_condition.wait()
                
                # Wait for current battles to finish if needed
                while self._battle_count_queue.full():
                    async with self._battle_end_condition:
                        await self._battle_end_condition.wait()
                
                await self._battle_semaphore.acquire()

                # Wait for battle to complete and get outcome
                battle_complete = False
                while not battle_complete and len(self._battles) > 0:
                    battle = list(self._battles.values())[-1]
                    if battle.won is not None:  # Battle has finished
                        battle_complete = True
                        outcome = "win" if battle.won else "loss"
                        rating = getattr(battle, 'rating', None)
                        ic(f"Battle {completed_games + 1} completed: {outcome}, Rating: {rating}")
                        self._battle_logger.end_game(outcome, rating)
                        self._game_started = False
                        completed_games += 1
                    await asyncio.sleep(0.1)  # Small delay to prevent busy waiting

        # Wait for any remaining battles to complete
        await self._battle_count_queue.join()

        ic(f"Laddering ({n_games} battles) finished in {perf_counter() - start_time}s")

    def choose_move(self, battle):
        """Override choose_move to add logging for each turn."""
        # Get battle state and decision
        battle_state = format_battle_prompt(battle, self.LLM_model)
        # ic(battle_state) # Debugging
        thought, action_type, action_name = move_prompt(battle_state, self.LLM_model)

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