import os
from datetime import datetime
import json
from pathlib import Path
from icecream import ic

class BattleLogger:
    def __init__(self, base_dir="logs"):
        """Initialize the battle logger with a base directory for logs."""
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(exist_ok=True)
        self.current_game_file = None
        self.current_game_data = None
        self.model_name = None

    def start_new_game(self, game_type, model_name, player_name):
        """
        Start logging a new game.
        
        Args:
            game_type (str): Type of game being played ('local' or 'ladder')
            model_name (str): Name of the LLM model being used
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        game_dir = self.base_dir / timestamp
        game_dir.mkdir(exist_ok=True)
        
        self.model_name = model_name
        
        self.current_game_data = {
            "metadata": {
                "game_type": game_type,
                "start_time": datetime.now().isoformat(),
                "end_time": None,
                "outcome": None,
                "final_rank": None if game_type != "ladder" else 0,
                "llm_model": self.model_name,
                "player_name": player_name,
                "random_move_count": 0,
                "total_move_count": 0
            },
            "turns": []
        }
        
        self.current_game_file = game_dir / "battle_log.json"
        self._save_current_game()

    def log_turn(self, turn_number, battle_state, thought, action_type, action_name, is_random=False, consensus=None, voting=None):
        """
        Log a single turn of the battle.
        
        Args:
            turn_number (int): Current turn number
            battle_state (str): Current state of the battle
            thought (str): LLM's reasoning for the move
            action_type (str): Type of action taken (move/switch)
            action_name (str): Name of the specific action
            is_random (bool): Whether this was a random move or not
        """
        if self.current_game_data is None:
            raise ValueError("No active game logging session. Call start_new_game first.")
        
        turn_data = {
            "turn_number": turn_number,
            "battle_state": battle_state,
            "thought": thought,
            "action_type": action_type,
            "action_name": action_name,
            "is_random_move": is_random,
            "timestamp": datetime.now().isoformat(),
            "consensus": consensus,
            "voting": voting
        }
        
        # Update metadata counters
        self.current_game_data["metadata"]["total_move_count"] += 1
        if is_random:
            self.current_game_data["metadata"]["random_move_count"] += 1
        
        self.current_game_data["turns"].append(turn_data)
        self._save_current_game()

    def end_game(self, outcome, final_rank=None):
        """End the current game logging session."""
        if self.current_game_data is None:
            raise ValueError("No active game logging session. Call start_new_game first.")
        
        self.current_game_data["metadata"]["end_time"] = datetime.now().isoformat()
        self.current_game_data["metadata"]["outcome"] = outcome
        if final_rank is not None:
            self.current_game_data["metadata"]["final_rank"] = final_rank
            
        # Calculate and add random move percentage to metadata
        total_moves = self.current_game_data["metadata"]["total_move_count"]
        random_moves = self.current_game_data["metadata"]["random_move_count"]
        random_move_percentage = (random_moves / total_moves * 100) if total_moves > 0 else 0
        self.current_game_data["metadata"]["random_move_percentage"] = round(random_move_percentage, 2)
        
        self._save_current_game()
        
        self.current_game_data = None
        self.current_game_file = None

    def _save_current_game(self):
        """Save the current game data to file."""
        if self.current_game_file is None:
            raise ValueError("No active game file.")
        
        with open(self.current_game_file, 'w') as f:
            json.dump(self.current_game_data, f, indent=2)