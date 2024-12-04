# website/Services/texasholdem_poker_service.py

import logging
import asyncio
import os
from daphne.server import Server
from .Logic.PokerGame import HoldemPokerGameFactory
from .Logic.Game_RoomServer import GameRoomFactory, GameServer
from .Logic.Game_server_instance import set_game_server_instance
from typing import Optional  # Add this import

# Configure the logger
logger = logging.getLogger("TexasHoldemServer")
logger.setLevel(logging.INFO)  # Set to INFO or DEBUG as needed

# Add a console handler with a formatter
handler = logging.StreamHandler()
formatter = logging.Formatter('[%(asctime)s] %(levelname)s:%(name)s:%(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

def initialize_game_server() -> Optional[GameServer]:
    """
    Initializes the GameServer and sets the global game_server_instance.
    """
    try:
        # Create the game factory and room factory
        game_factory = HoldemPokerGameFactory(big_blind=50, small_blind=25, logger=logger)
        game_room_factory = GameRoomFactory(game_factory=game_factory, room_size=10, logger=logger)
        game_server = GameServer(room_factory=game_room_factory, logger=logger)

        set_game_server_instance(game_server)
        logger.info("Game server initialized successfully.")
        return game_server
    except Exception as e:
        logger.exception(f"Failed to initialize game server: {e}")
        return None

async def main():
    # Initialize the game server
    game_server = initialize_game_server()
    if game_server:
        # Start the game server in the background
        asyncio.create_task(game_server.start())
        logger.info("Game server running")
    else:
        logger.error("Game server not initialized. Exiting.")
        exit(1)

    # Ensure DJANGO_SETTINGS_MODULE is set
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'addiction.settings')

    # Import the ASGI application from addiction.asgi
    try:
        from addiction.asgi import application
    except ImportError as e:
        logger.exception(f"Failed to import ASGI application: {e}")
        exit(1)

    # Configure Daphne server
    server = Server(
        application=application,
        endpoints=["tcp:port=8000:interface=127.0.0.1"],  # Adjust port and interface as needed
        signal_handlers=False
    )

    logger.info("Starting Daphne server on 127.0.0.1:8000")

    # Start Daphne server in a separate thread to avoid blocking the event loop
    await asyncio.to_thread(server.run)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Server stopped by user.")
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
