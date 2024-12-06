# website/Services/Logic/game_server_instance.py

from typing import Optional
import logging
from .Game_RoomServer import GameServer  # Import GameServer from Game_RoomServer

_game_server_instance: Optional[GameServer] = None

logger = logging.getLogger("GameServerInstance")

def set_game_server_instance(instance: GameServer) -> None:
    global _game_server_instance
    _game_server_instance = instance
    logger.info(f"Game server instance set: {instance}")

def get_game_server_instance() -> Optional[GameServer]:
    return _game_server_instance
