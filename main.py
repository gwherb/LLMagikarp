import asyncio
from poke_env import AccountConfiguration, ShowdownServerConfiguration
from poke_env.player import RandomPlayer, SimpleHeuristicsPlayer
from players import *

async def local():

    # Create Player 1
    LLMagikarp = LoggingPlayer()

    # Create Player 2
    HeuristicsPlayer = SimpleHeuristicsPlayer()

    # Start the battle
    await LLMagikarp.battle_against(HeuristicsPlayer, n_battles=1)

async def server():

    # Create Bot
    player = RandomPlayer(
        account_configuration=AccountConfiguration("gwherb", "Just4Gh!"),
        server_configuration=ShowdownServerConfiguration,
    )

    await player.send_challenges("LLMagikarp", n_challenges=1)


if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(local())

