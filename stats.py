from pathlib import Path
import json
from icecream import ic
from datetime import datetime
import argparse
import re
import csv

def get_battle_logs(logs_dir="./logs", start_date=None, end_date=None):
    logs_path = Path(logs_dir)
    
    for log_file in logs_path.glob("**/battle_log.json"):
        try:
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

def get_stats(stats_dict, game_type, start_date, end_date, model=None, player=None):
    for battle_log in get_battle_logs(start_date=start_date, end_date=end_date):
        try:
            if battle_log["metadata"]["game_type"] != game_type:
                continue

            if model and battle_log["metadata"]["llm_model"] != model:
                continue

            if player and battle_log["metadata"]["player_name"] != player:
                continue

            if player:
                start_date = "20241030_000000"
                end_date = "20250101_000000"

            prev_switch = False
            turns = []

            stats_dict["games_played"] += 1
            stats_dict['total_random_moves'] += battle_log["metadata"].get("random_move_count", 0)
            
            if battle_log["metadata"]["outcome"] == "win":
                stats_dict["wins"] += 1
            elif battle_log["metadata"]["outcome"] == "loss":
                stats_dict["losses"] += 1
                # Check if turns exist and there's at least one turn
                if battle_log.get("turns") and len(battle_log["turns"]) > 0:
                    last_turn_state = battle_log["turns"][-1].get("battle_state", "")
                    remaining_pokemon = re.search('Remaining Pokemon: (\d)/', last_turn_state)
                    if remaining_pokemon and int(remaining_pokemon.group(1)) <= 2:
                        stats_dict["close_losses"] += 1
                    elif remaining_pokemon and int(remaining_pokemon.group(1)) >= 5:
                        stats_dict["total_defeats"] += 1
            else:
                stats_dict["error_matches"] += 1

            if not battle_log.get("turns"):
                continue

            for turn in battle_log["turns"]:
                if turn.get("action_type") == "switch":
                    if prev_switch:
                        stats_dict["double_switches"] += 1
                    prev_switch = True
                    stats_dict["total_switches"] += 1
                    turns.append(0)
                elif turn.get("action_type") == "move":
                    stats_dict["total_attacks"] += 1
                    prev_switch = False
                    turns.append(1)
                
                if "consensus" in turn:
                    stats_dict["sc3_turns"] += 1
                    if turn["consensus"]:
                        stats_dict["sc3_consensus_turns"] += 1

            total_turns = len(turns)
            if total_turns > 0:
                stats_dict["avg_turns"] += total_turns
                late_game_start = round(total_turns * 0.75)
                stats_dict["avg_late_game_switches"] += sum(turns[late_game_start:])
        
        except Exception as e:
            ic(f"Error processing battle log: {e}")
            continue
    
    if stats_dict["games_played"] > 0:
        stats_dict["avg_turns"] /= stats_dict["games_played"]
        stats_dict["avg_late_game_switches"] /= stats_dict["games_played"]
        stats_dict["sc3_consensus_percentage"] = stats_dict["sc3_consensus_turns"] / stats_dict["sc3_turns"] * 100 if stats_dict["sc3_turns"] > 0 else 0
        stats_dict["win_percentage"] = stats_dict["wins"] / (stats_dict["games_played"] - stats_dict["error_matches"]) * 100 if (stats_dict["games_played"] - stats_dict["error_matches"]) > 0 else 0
    
    return stats_dict

def write_stats_to_csv(all_stats, filename="pokemon_battle_stats.csv"):
    fieldnames = [
        "player", "model", "game_type", "games_played", "wins", "losses", 
        "win_percentage", "error_matches", "total_random_moves", "total_attacks",
        "total_switches", "double_switches", "close_losses", "total_defeats",
        "avg_turns", "avg_late_game_switches", "sc3_consensus_percentage",
        "sc3_consensus_turns", "sc3_turns"
    ]
    
    with open(filename, 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for stat in all_stats:
            writer.writerow(stat)

def stats(start_date='20241030_000000', end_date='20250101_000000', model=None, player=None):
    parser = argparse.ArgumentParser(description="Get stats from Pokemon Showdown logs")
    parser.add_argument("--start", type=str, help="Start date for logs")
    parser.add_argument("--end", type=str, help="End date for logs")
    parser.add_argument("--model", type=str, help="Model to use for completion")
    parser.add_argument("--player", type=str, help="Player to get stats for")

    args = parser.parse_args()
    if args.start:
        start_date = args.start
    if args.end:
        end_date = args.end
    if args.model:
        model = args.model
    if args.player:
        player = args.player

    stats_template = {
        "games_played": 0, "wins": 0, "losses": 0, "win_percentage": 0,
        "error_matches": 0, "total_random_moves": 0, "total_attacks": 0,
        "total_switches": 0, "double_switches": 0, "close_losses": 0,
        "total_defeats": 0, "avg_turns": 0, "avg_late_game_switches": 0,
        "sc3_consensus_percentage": 0, "sc3_consensus_turns": 0, "sc3_turns": 0
    }

    all_stats = []
    players = ['LoggingPlayer', 'SC3Player', 'MemoryPlayer', 'OppositionPlayer', 'InitialStrategyPlayer']
    models = ['gpt-4o', 'gpt-4o-mini']
    game_types = ['local', 'ladder']

    for current_player in players:
        for current_model in models:
            for game_type in game_types:
                stats_dict = stats_template.copy()
                stats_dict = get_stats(
                    stats_dict, 
                    game_type, 
                    start_date, 
                    end_date, 
                    model=current_model, 
                    player=current_player
                )
                
                # Add metadata to stats
                stats_dict['player'] = current_player
                stats_dict['model'] = current_model
                stats_dict['game_type'] = game_type
                
                all_stats.append(stats_dict)

    # Write all stats to CSV
    write_stats_to_csv(all_stats)
    ic(f"Stats have been written to pokemon_battle_stats.csv")

if __name__ == "__main__":
    stats()