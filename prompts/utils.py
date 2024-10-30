from pathlib import Path
import os

def load_prompt(filename):
    prompt_path = Path("prompts") / filename
    with open(prompt_path, "r", encoding="utf-8") as f:
        return f.read().strip()