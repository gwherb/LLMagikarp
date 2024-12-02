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
                start = datetime.strptime(start_date, "%Y%m%d_%H%M%S")
                end = datetime.strptime(end_date, "%Y%m%d_%H%M%S")

                if start <= timestamp <= end:
                    with open(log_file, "r") as f:
                        yield json.load(f), log_file
            else:
                with open(log_file, "r") as f:
                    yield json.load(f), log_file
        except Exception as e:
            ic(f"Error processing {log_file}: {e}")
            continue

def rectify_log_metadata():
    """
    Rectify metadata in battle logs, adding player_name based on parent folder timestamp
    """
    modified_count = 0
    
    # Define date ranges for processing
    date_ranges = [
        ("20241030_000000", "20241124_160000", "LoggingPlayer"),
        ("20241124_160000", "20241125_160000", "SC3Player"),
        ("20241125_160000", "20241125_230000", "MemoryPlayer"),
        ("20241125_230000", "20241126_100200", "OppositionPlayer"),
    ]

    # Process each date range
    for start_date, end_date, player_name in date_ranges:
        for battle_log, log_file in get_battle_logs(start_date=start_date, end_date=end_date):
            try:
                # Initialize metadata if it doesn't exist
                if "metadata" not in battle_log:
                    battle_log["metadata"] = {}
                
                # Add player_name if missing
                if "player_name" not in battle_log["metadata"]:
                    battle_log["metadata"]["player_name"] = player_name
                    
                    # Save the modified log back to file using the actual log_file path
                    with open(log_file, "w") as f:
                        json.dump(battle_log, f, indent=2)
                    modified_count += 1
                    ic(f"Added {player_name} to {log_file}")
                    
            except Exception as e:
                ic(f"Error rectifying log: {e}")
                continue
            
    return modified_count

if __name__ == '__main__':
    modified = rectify_log_metadata()
    print(f"Modified {modified} log files")