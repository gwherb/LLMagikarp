import asyncio
from poke_env import AccountConfiguration, ShowdownServerConfiguration
from poke_env.player import RandomPlayer
from players import TestPlayer

async def local():

    # Create Player 1
    random_player_1 = RandomPlayer()

    # Create Player 2
    random_player_2 = TestPlayer()

    # Start the battle
    await random_player_1.battle_against(random_player_2, n_battles=1)

async def server():

    # Create Bot
    player = RandomPlayer(
        account_configuration=AccountConfiguration("gwherb", "Just4Gh!"),
        server_configuration=ShowdownServerConfiguration,
    )

    await player.send_challenges("LLMagikarp", n_challenges=1)


if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(local())

