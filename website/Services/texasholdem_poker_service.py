# website/Services/texasholdem_poker_service.py

import logging
import asyncio
import os
import sys
import signal
from daphne.server import Server
from .Logic.PokerGame import HoldemPokerGameFactory
from .Logic.Game_RoomServer import GameRoomFactory, GameServer
from .Logic.Game_server_instance import set_game_server_instance
from typing import Optional

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

async def start_daphne_server(application, host: str = "127.0.0.1", port: int = 8000):
    """
    Starts the Daphne ASGI server.
    """
    server = Server(
        application=application,
        endpoints=[f"tcp:port={port}:interface={host}"],
        signal_handlers=False  # We'll handle signals manually
    )

    logger.info(f"Starting Daphne server on {host}:{port}")
    await asyncio.to_thread(server.run)

async def main():
    # Ensure DJANGO_SETTINGS_MODULE is set before anything else
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'addiction.settings')  # Replace 'addiction' if your project has a different name

    # Initialize Django
    import django
    django.setup()
    logger.info("Django setup completed.")

    # Import the ASGI application after Django setup
    try:
        from addiction.asgi import application  # Replace 'addiction' with your project name if different
    except ImportError as e:
        logger.exception(f"Failed to import ASGI application: {e}")
        sys.exit(1)

    # Initialize the game server
    game_server = initialize_game_server()
    if game_server:
        # Start the game server in the background
        asyncio.create_task(game_server.start())
        logger.info("Game server started as a background task.")
    else:
        logger.error("Game server not initialized. Exiting.")
        sys.exit(1)

    # Start Daphne server
    await start_daphne_server(application, host="127.0.0.1", port=8002)

def shutdown(signal_num, frame):
    """
    Handles shutdown signals to gracefully terminate the server.
    """
    logger.info(f"Received exit signal {signal_num}. Shutting down...")
    sys.exit(0)

if __name__ == "__main__":
    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Server stopped by user via KeyboardInterrupt.")
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
