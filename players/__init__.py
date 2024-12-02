from .TestPlayer import TestPlayer
from .LoggingPlayer import LoggingPlayer
from .SC3Player import SC3Player
from .MemoryPlayer import MemoryPlayer
from .OppositionPlayer import OppositionPlayer
from .InitialStrategyPlayer import InitialStrategyPlayer

# Import other player classes here
# from .AnotherPlayer import AnotherPlayer
# from .YetAnotherPlayer import YetAnotherPlayer

# You can also import everything from a module like this:
# from .TestPlayer import *

# If you want to control what gets imported when someone does `from players import *`,
# you can define __all__:
__all__ = ['TestPlayer', 'LoggingPlayer', 'SC3Player', 'MemoryPlayer', 'OppositionPlayer', 'InitialStrategyPlayer']  # Add other player names to this list as needed
