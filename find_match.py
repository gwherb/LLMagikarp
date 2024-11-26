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
                        yield json.load(f), log_file
            else:
                with open(log_file, "r") as f:
                    yield json.load(f), log_file
        except Exception as e:
            ic(f"Error processing {log_file}: {e}")
            continue

def main():    
    for battle_log in get_battle_logs(start_date="20241012_000000", end_date="20251012_000000"):
        for turn in battle_log[0]["turns"]:
            if "BATTLE STATE - TURN 10\n============================\n\nPREVIOUS TURN (8):\nDecidueye was switched in at 100% HP but took 12% damage from Stealth Rock. Houndstone then used Body Press" in turn["battle_state"]:
                # print battle log folder name
                print(battle_log[1].parent.name)
                break

if __name__ == "__main__":
    main()