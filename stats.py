from pathlib import Path
import json
from icecream import ic
from datetime import datetime

def get_battle_logs(logs_dir="./logs", start_date=None, end_date=None):
    logs_path = Path(logs_dir)
    
    for log_file in logs_path.glob("**/battle_log.json"):
        try:
            # Get timestamp from the log file's parent directory
            timestamp_str = log_file.parent.name
            timestamp = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")

            if start_date and end_date:
                start = datetime.strptime(start_date, "%Y%m%d")
                end = datetime.strptime(end_date, "%Y%m%d")

                if start <= timestamp <= end:
                    with open(log_file, "r") as f:
                        yield json.load(f)
            else:
                with open(log_file, "r") as f:
                    yield json.load(f)
        except Exception as e:
            ic(f"Error processing {log_file}: {e}")
            continue

if __name__ == "__main__":
    start_date = "20241001"  # Fixed date format to match parsing
    end_date = "20241112"

    local_stats = {
        "games_played": 0,
        "wins": 0,
        "losses": 0,
        "error_matches": 0,
        "total_random_moves": 0,
        "total_attacks": 0,
        "total_switches": 0,
    }

    ladder_stats = {
        "games_played": 0,
        "wins": 0,
        "losses": 0,
        "error_matches": 0,
        "total_random_moves": 0,
        "total_attacks": 0,
        "total_switches": 0,
    }

    for battle_log in get_battle_logs(start_date=start_date, end_date=end_date):
        if battle_log["metadata"]["game_type"] == "local":
            local_stats["games_played"] += 1
            local_stats['total_random_moves'] += battle_log["metadata"]["random_move_count"]
            
            if battle_log["metadata"]["outcome"] == "win":
                local_stats["wins"] += 1
            elif battle_log["metadata"]["outcome"] == "loss":
                local_stats["losses"] += 1
            else:
                local_stats["error_matches"] += 1

            for turn in battle_log["turns"]:
                local_stats["total_attacks"] += 1 if turn["action_type"] == "move" else 0
                local_stats["total_switches"] += 1 if turn["action_type"] == "switch" else 0
        elif battle_log["metadata"]["game_type"] == "ladder":
            ladder_stats["games_played"] += 1
            ladder_stats['total_random_moves'] += battle_log["metadata"]["random_move_count"]
            
            if battle_log["metadata"]["outcome"] == "win":
                ladder_stats["wins"] += 1
            elif battle_log["metadata"]["outcome"] == "loss":
                ladder_stats["losses"] += 1
            else:
                ladder_stats["error_matches"] += 1

            for turn in battle_log["turns"]:
                ladder_stats["total_attacks"] += 1 if turn["action_type"] == "move" else 0
                ladder_stats["total_switches"] += 1 if turn["action_type"] == "switch" else 0

    ic("From {} to {}".format(start_date, end_date))
    ic(local_stats)
    ic(ladder_stats)