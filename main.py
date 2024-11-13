import asyncio
from poke_env import AccountConfiguration, ShowdownServerConfiguration
from poke_env.player import RandomPlayer, SimpleHeuristicsPlayer
from players import *
import argparse

async def local(n_battles=1):

    # Create Player 1
    LLMagikarp = LoggingPlayer()

    # Create Player 2
    HeuristicsPlayer = SimpleHeuristicsPlayer()

    # Start the battle
    await LLMagikarp.battle_against(HeuristicsPlayer, n_battles=n_battles)

async def server(n_challenges=1):

    # Create Bot
    player = RandomPlayer(
        account_configuration=AccountConfiguration("gwherb", "Just4Gh!"),
        server_configuration=ShowdownServerConfiguration,
    )

    await player.send_challenges("LLMagikarp", n_challenges=n_challenges)

async def ladder(n_battles=1):

    LLMagikarp = LoggingPlayer(
        account_configuration=AccountConfiguration("gwherb", "Just4Gh!"),
        server_configuration=ShowdownServerConfiguration,
    )

    await LLMagikarp.ladder(n_battles)

    for battle in LLMagikarp.battles.values():
        print(battle.rating, battle.opponent_rating)

def main():
    parser = argparse.ArgumentParser(description="Run a Pokemon Showdown bot")
    parser.add_argument("--mode", type=str, help="Mode to run the bot in")
    parser.add_argument("--battle_num", type=int, help="Number of battles to run")

    args = parser.parse_args()

    if args.mode == "local":
        asyncio.get_event_loop().run_until_complete(local(args.battle_num))
    elif args.mode == "server":
        asyncio.get_event_loop().run_until_complete(server(args.battle_num))
    elif args.mode == "ladder":
        asyncio.get_event_loop().run_until_complete(ladder(args.battle_num))
    else:
        print("Invalid mode")

if __name__ == "__main__":
    main()

