from pathlib import Path
import json
from icecream import ic
from datetime import datetime
import argparse
import re

def get_battle_logs(logs_dir="./logs", start_date=None, end_date=None):
    logs_path = Path(logs_dir)
    
    for log_file in logs_path.glob("**/battle_log.json"):
        try:
            # Get timestamp from the log file's parent directory
            timestamp_str = log_file.parent.name
            timestamp = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")

            if start_date and end_date:
                start = datetime.strptime(start_date, "%Y%m%d_%H%M%S")
                end = datetime.strptime(end_date, "%Y%m%d_%H%M%S")

                if start <= timestamp <= end:
                    with open(log_file, "r") as f:
                        yield json.load(f)
            else:
                with open(log_file, "r") as f:
                    yield json.load(f)
        except Exception as e:
            ic(f"Error processing {log_file}: {e}")
            continue

def get_stats(stats_dict, game_type, start_date, end_date, model=None):
    for battle_log in get_battle_logs(start_date=start_date, end_date=end_date):
        # Skip if this battle log isn't for the game type we're currently processing
        if battle_log["metadata"]["game_type"] != game_type:
            continue

        if model and battle_log["metadata"]["llm_model"] != model:
            continue

        prev_switch = False
        turns = []  # List to store the turns of the match

        stats_dict["games_played"] += 1
        stats_dict['total_random_moves'] += battle_log["metadata"]["random_move_count"]
        
        if battle_log["metadata"]["outcome"] == "win":
            stats_dict["wins"] += 1
        elif battle_log["metadata"]["outcome"] == "loss":
            stats_dict["losses"] += 1
            last_turn_state = battle_log["turns"][-1]["battle_state"]
            remaining_pokemon = re.search('Remaining Pokemon: (\d)/', last_turn_state)
            if remaining_pokemon and int(remaining_pokemon.group(1)) <= 2:
                stats_dict["close_losses"] += 1
            elif remaining_pokemon and int(remaining_pokemon.group(1)) >= 5:
                stats_dict["total_defeats"] += 1
        else:
            stats_dict["error_matches"] += 1

        sc3_turns = 0
        consensus_turns = 0
        for turn in battle_log["turns"]:
            if turn["action_type"] == "switch":
                if prev_switch:
                    stats_dict["double_switches"] += 1
                prev_switch = True

                stats_dict["total_switches"] += 1
                turns.append(0)

            elif turn["action_type"] == "move":
                stats_dict["total_attacks"] += 1
                prev_switch = False
                turns.append(1)
            
            if "consensus" in turn:
                stats_dict["sc3_turns"] += 1
                if turn["consensus"]:
                    stats_dict["sc3_consensus_turns"] += 1

        total_turns = len(turns)
        stats_dict["avg_turns"] += total_turns

        stats_dict["avg_late_game_switches"] += sum(turns[round(total_turns * 0.75):])
    
    # Calculate averages if games were played
    if stats_dict["games_played"] > 0:
        stats_dict["avg_turns"] /= stats_dict["games_played"]
        stats_dict["avg_late_game_switches"] /= stats_dict["games_played"]
        stats_dict["sc3_consensus_percentage"] = stats_dict["sc3_consensus_turns"] / stats_dict["sc3_turns"] * 100 if stats_dict["sc3_turns"] > 0 else 0
        stats_dict["win_percentage"] = stats_dict["wins"] / (stats_dict["games_played"] - stats_dict["error_matches"]) * 100
    
    return stats_dict

def stats(start_date='20241030_000000', end_date='20250101_000000', model=None):
    parser = argparse.ArgumentParser(description="Get stats from Pokemon Showdown logs")
    parser.add_argument("--start", type=str, help="Start date for logs")
    parser.add_argument("--end", type=str, help="End date for logs")
    parser.add_argument("--model", type=str, help="Model to use for completion")

    args = parser.parse_args()
    if args.start:
        start_date = args.start
    if args.end:
        end_date = args.end
    if args.model:
        model = args.model

    local_stats = {
        "games_played": 0,
        "wins": 0,
        "losses": 0,
        "win_percentage": 0,
        "error_matches": 0,
        "total_random_moves": 0,
        "total_attacks": 0,
        "total_switches": 0,
        "double_switches": 0,
        "close_losses": 0,
        "total_defeats": 0,
        "avg_turns": 0,
        "avg_late_game_switches": 0,
        "sc3_consensus_percentage": 0,
        "sc3_consensus_turns": 0,
        "sc3_turns": 0
    }

    ladder_stats = {
        "games_played": 0,
        "wins": 0,
        "losses": 0,
        "win_percentage": 0,
        "error_matches": 0,
        "total_random_moves": 0,
        "total_attacks": 0,
        "total_switches": 0,
        "double_switches": 0,
        "close_losses": 0,
        "total_defeats": 0,
        "avg_turns": 0,
        "avg_late_game_switches": 0,
        "sc3_consensus_percentage": 0,
        "sc3_consensus_turns": 0,
        "sc3_turns": 0
    }

    # Process each type of game separately
    local_stats = get_stats(local_stats, "local", start_date, end_date, model=model)
    ladder_stats = get_stats(ladder_stats, "ladder", start_date, end_date, model=model)


    ic("From {} to {}".format(start_date, end_date))
    ic(local_stats)
    ic(ladder_stats)

if __name__ == "__main__":
    # Initial Runs (Zero Shot):
    ic("Initial Run")
    stats(start_date='20241030_000000', end_date='2024112_000000')

    ic("-----------------------------------")
    
    # Addition of stats for Pokemon in description (Zero Shot):
    ic("Addition of stats for Pokemon in description")
    stats(start_date='20241112_000000', end_date='20241119_000000')

    ic("-----------------------------------")

    # 3 Shot Model:
    ic("3 Shot Model gpt-4o-mini")
    stats(start_date='20241119_000000', end_date='20241124_140000', model='gpt-4o-mini')

    ic("3 Shot Model gpt-4o")
    stats(start_date='20241119_000000', end_date='20241124_140000', model='gpt-4o')

    ic("-----------------------------------")

    # SC-3 Model:
    ic("SC-3 Model gpt-4o-mini")
    stats(start_date='20241124_140000', end_date='20241201_000000', model='gpt-4o-mini')

    ic("SC-3 Model gpt-4o")
    stats(start_date='20241124_140000', end_date='20241125_170000', model='gpt-4o')

    # Memory Model (no SC):
    ic("Memory Model gpt-4o-mini")
    stats(start_date='20241125_170000', end_date='20250101_000000', model='gpt-4o-mini')