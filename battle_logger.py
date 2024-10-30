import os
from datetime import datetime
import json
from pathlib import Path
from poke_env import Player
from icecream import ic

class BattleLogger:
    def __init__(self, base_dir="logs"):
        """Initialize the battle logger with a base directory for logs."""
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(exist_ok=True)
        self.current_game_file = None
        self.current_game_data = None

    def start_new_game(self, game_type):
        """Start logging a new game."""
        # Create timestamp for filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Create game-specific directory with timestamp
        game_dir = self.base_dir / timestamp
        game_dir.mkdir(exist_ok=True)
        
        # Initialize the game data structure
        self.current_game_data = {
            "metadata": {
                "game_type": game_type,
                "start_time": datetime.now().isoformat(),
                "end_time": None,
                "outcome": None,
                "final_rank": None if game_type != "ladder" else 0
            },
            "turns": []
        }
        
        # Set the current game file path
        self.current_game_file = game_dir / "battle_log.json"
        
        # Save initial game data
        self._save_current_game()

    def log_turn(self, turn_number, battle_state, thought, action_type, action_name):
        """Log a single turn of the battle."""
        if self.current_game_data is None:
            raise ValueError("No active game logging session. Call start_new_game first.")
        
        turn_data = {
            "turn_number": turn_number,
            "battle_state": battle_state,
            "thought": thought,
            "action_type": action_type,
            "action_name": action_name,
            "timestamp": datetime.now().isoformat()
        }
        
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
        
        self._save_current_game()
        
        # Clear current game data
        self.current_game_data = None
        self.current_game_file = None

    def _save_current_game(self):
        """Save the current game data to file."""
        if self.current_game_file is None:
            raise ValueError("No active game file.")
        
        with open(self.current_game_file, 'w') as f:
            json.dump(self.current_game_data, f, indent=2)
