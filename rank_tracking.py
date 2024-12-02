from pathlib import Path
import json
from icecream import ic
from datetime import datetime
import argparse
import csv

def get_battle_logs(logs_dir="./logs", start_date=None, end_date=None):
    """Retrieves battle logs from the specified directory within the date range."""
    logs_path = Path(logs_dir)
    
    for log_file in logs_path.glob("**/battle_log.json"):
        try:
            with open(log_file, "r") as f:
                log_data = json.load(f)
                
                # Skip logs without rank data or with rank 0
                final_rank = log_data["metadata"].get("final_rank")
                if final_rank is None or final_rank == 0:
                    continue
                    
                timestamp = datetime.fromisoformat(log_data["metadata"]["start_time"])
                
                if start_date and end_date:
                    start = datetime.strptime(start_date, "%Y%m%d_%H%M%S")
                    end = datetime.strptime(end_date, "%Y%m%d_%H%M%S")

                    if start <= timestamp <= end:
                        yield log_data, timestamp
                else:
                    yield log_data, timestamp
                    
        except Exception as e:
            ic(f"Error processing {log_file}: {e}")
            continue

def track_rankings(start_date='20241030_000000', end_date='20250101_000000', model=None, player=None):
    """Tracks rankings over time for specified players and models."""
    ranking_data = []
    total_games = 0
    valid_games = 0
    zero_rank_games = 0
    null_rank_games = 0
    
    for battle_log, timestamp in get_battle_logs(start_date=start_date, end_date=end_date):
        try:
            total_games += 1
            metadata = battle_log["metadata"]
            
            # Skip if we're filtering by model and this isn't the right one
            if model and metadata["llm_model"] != model:
                continue

            # Skip if we're filtering by player and this isn't the right one
            if player and metadata["player_name"] != player:
                continue

            # Track valid games
            final_rank = metadata["final_rank"]
            if final_rank is not None and final_rank > 0:
                valid_games += 1
                game_data = {
                    "timestamp": timestamp,
                    "player": metadata["player_name"],
                    "model": metadata["llm_model"],
                    "final_rank": final_rank,
                    "outcome": metadata["outcome"],
                    "random_move_percentage": metadata.get("random_move_percentage", 0)
                }
                ranking_data.append(game_data)
            elif final_rank == 0:
                zero_rank_games += 1
            else:
                null_rank_games += 1

        except Exception as e:
            ic(f"Error processing battle log: {e}")
            continue
    
    # Sort by timestamp
    ranking_data.sort(key=lambda x: x["timestamp"])
    
    ic(f"Total games processed: {total_games}")
    ic(f"Games with valid rank data (>0): {valid_games}")
    ic(f"Games with zero rank: {zero_rank_games}")
    ic(f"Games with null rank: {null_rank_games}")
    return ranking_data

def write_rankings_to_csv(ranking_data, filename="pokemon_ranking_data.csv"):
    """Writes ranking data to a CSV file."""
    if not ranking_data:
        ic("No ranking data to write")
        return

    fieldnames = [
        "timestamp", "player", "model", "final_rank", "outcome", "random_move_percentage"
    ]
    
    with open(filename, 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for entry in ranking_data:
            writer.writerow(entry)

def main():
    parser = argparse.ArgumentParser(description="Track Pokemon Showdown rankings over time")
    parser.add_argument("--start", type=str, help="Start date for logs (format: YYYYMMDD_HHMMSS)")
    parser.add_argument("--end", type=str, help="End date for logs (format: YYYYMMDD_HHMMSS)")
    parser.add_argument("--model", type=str, help="Model to filter by")
    parser.add_argument("--player", type=str, help="Player to filter by")
    parser.add_argument("--output", type=str, help="Output CSV filename", default="pokemon_ranking_data.csv")
    
    args = parser.parse_args()
    
    start_date = args.start if args.start else '20241030_000000'
    end_date = args.end if args.end else '20250101_000000'
    
    # Get ranking data
    ranking_data = track_rankings(
        start_date=start_date,
        end_date=end_date,
        model=args.model,
        player=args.player
    )
    
    if not ranking_data:
        ic("No valid ranking data found")
        return
        
    # Write to CSV
    write_rankings_to_csv(ranking_data, args.output)
    ic(f"Ranking data has been written to {args.output}")
    
    # Print player statistics
    players = set(game["player"] for game in ranking_data)
    for player in players:
        player_games = [game for game in ranking_data if game["player"] == player]
        ic(f"\nStats for {player}:")
        ic(f"  Total ranked games: {len(player_games)}")
        ic(f"  Initial rank: {player_games[0]['final_rank']}")
        ic(f"  Final rank: {player_games[-1]['final_rank']}")
        ic(f"  Rank change: {player_games[-1]['final_rank'] - player_games[0]['final_rank']}")
        ic(f"  Win rate: {sum(1 for game in player_games if game['outcome'] == 'win') / len(player_games):.2%}")
        ic(f"  Average random move percentage: {sum(game['random_move_percentage'] for game in player_games) / len(player_games):.1f}%")

if __name__ == "__main__":
    main()