# LLMagikarp

### Setting up a local battle engine

1. Install Node.js v10+.
2. Clone the Pokémon Showdown repository and set it up:

```sh
git clone https://github.com/smogon/pokemon-showdown.git
cd pokemon-showdown
npm install
cp config/config-example.js config/config.js
node pokemon-showdown start --no-security
Enter "http://localhost:8000/" in your browsers.
``` 

### Configuring OpenAI API

Get OPENAI API from https://platform.openai.com/account/api-keys

```sh
export OPENAI_API_KEY=<your key>
```

### Running battles

Install requirements into python env then run:

```sh
python main.py --mode XXXX --battle_num XXXX --model XXXXX
```
