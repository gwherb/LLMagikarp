# LLMagikarp - Pokemon Battle AI

A competitive Pokemon battle AI powered by Large Language Models that can play Pokemon Showdown battles with strategic reasoning and move analysis.

## Features

- **Multiple AI Players**: Different implementations with varying strategies
  - `LoggingPlayer`: Basic LLM-powered player with battle logging
  - `SC3Player`: Self-consistency voting system (3 predictions per move)
  - `MemoryPlayer`: Retains previous turn reasoning for context
  - `OppositionPlayer`: Considers opponent prediction in strategy
  - `InitialStrategyPlayer`: Generates team strategy at battle start

- **Battle Analysis**: Comprehensive type effectiveness, stat estimation, and strategic reasoning
- **Logging System**: Detailed battle logs with turn-by-turn analysis and outcomes
- **Google Drive Integration**: Automatic upload/download of battle logs
- **Statistics Tracking**: Win rates, ranking progression, and performance metrics

## Setup

### 1. Pokemon Showdown Server
```bash
git clone https://github.com/smogon/pokemon-showdown.git
cd pokemon-showdown
npm install
cp config/config-example.js config/config.js
node pokemon-showdown start --no-security
```

### 2. Environment Setup
```bash
pip install -r requirements.txt
export OPENAI_API_KEY=<your-api-key>
```

### 3. Google Drive (Optional)
For battle log backup, add `credentials.json` from Google Cloud Console.

## Usage

### Local Battles
```bash
python main.py --mode local --battle_num 5 --model gpt-4o
```

### Ladder Battles
```bash
python main.py --mode ladder --battle_num 10 --model gpt-4o-mini
```

### Statistics
```bash
python stats.py --start 20241201_000000 --end 20241231_235959
python rank_tracking.py --player SC3Player --output rankings.csv
```

### Log Management
```bash
python upload_logs.py    # Upload to Google Drive
python download_logs.py  # Download from Google Drive
python log_diagnostics.py  # Check sync status
```

## Models Supported

- `gpt-4o` (recommended for competitive play)
- `gpt-4o-mini` (faster, cost-effective)

## Architecture

The AI analyzes battle states by:
1. Parsing Pokemon stats, types, and available moves
2. Calculating type effectiveness and damage predictions
3. Evaluating strategic options (attack vs switch)
4. Generating reasoning with LLM function calling
5. Executing optimal moves based on analysis

Battle logs capture complete decision-making process for analysis and improvement.
