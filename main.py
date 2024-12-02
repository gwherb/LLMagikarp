import asyncio
from poke_env import AccountConfiguration, ShowdownServerConfiguration
from poke_env.player import RandomPlayer, SimpleHeuristicsPlayer
from players import *
import argparse

async def local(n_battles=1, model=None):

    # Create Player 1
    LLMagikarp = MemoryPlayer(model=model)

    # Create Player 2
    HeuristicsPlayer = SimpleHeuristicsPlayer()

    # Start the battle
    await LLMagikarp.battle_against(HeuristicsPlayer, n_battles=n_battles)

async def server(n_challenges=1, model=None):

    # Create Bot
    player = SimpleHeuristicsPlayer(
        account_configuration=AccountConfiguration("gwherb", "Just4Gh!"),
        server_configuration=ShowdownServerConfiguration,
    )

    await player.send_challenges("LLMagikarp", n_challenges=n_challenges)

async def ladder(n_battles=1, model=None):

    LLMagikarp = SC3Player(
        account_configuration=AccountConfiguration("gwherb", "Just4Gh!"),
        server_configuration=ShowdownServerConfiguration,
        start_timer_on_battle_start=True,
        model=model
    )

    await LLMagikarp.ladder(n_battles)

    for battle in LLMagikarp.battles.values():
        print(battle.rating, battle.opponent_rating)

def main():
    parser = argparse.ArgumentParser(description="Run a Pokemon Showdown bot")
    parser.add_argument("--mode", type=str, help="Mode to run the bot in")
    parser.add_argument("--battle_num", type=int, help="Number of battles to run")
    parser.add_argument("--model", type=str, help="Model to use for completion")

    model = 'gpt-4o-mini'
    args = parser.parse_args()
    if args.model:
        model = args.model

    if args.mode == "local":
        asyncio.get_event_loop().run_until_complete(local(args.battle_num, model))
    elif args.mode == "server":
        asyncio.get_event_loop().run_until_complete(server(args.battle_num, model))
    elif args.mode == "ladder":
        asyncio.get_event_loop().run_until_complete(ladder(args.battle_num, model))
    else:
        print("Invalid mode")

if __name__ == "__main__":
    main()

