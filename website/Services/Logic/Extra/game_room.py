# # website/Services/Logic/game_room.py

# import asyncio
# from typing import List, Dict, Set, Generator, Optional
# import logging
# from .poker_game import GameSubscriber, GameError
# from .player_server import PlayerServer
# from .poker_game_holdem import HoldemPokerGameFactory  # Ensure correct import

# class FullGameRoomException(Exception):
#     """Exception raised when attempting to join a full game room."""
#     pass


# class GameRoom(GameSubscriber):
#     def __init__(self, id: str, game_factory, logger: Optional[logging.Logger] = None):
#         self.id = id
#         self.private = False
#         self.active = False
#         self._game_factory = game_factory
#         self._room_size = 10
#         self._logger = logger or logging.getLogger(__name__)
#         self.players: Dict[str, PlayerServer] = {}
#     async def deactivate(self):
#         self.active = False
#         # Perform any cleanup necessary
#         self.logger.info(f"Room {self.id} is deactivating.")
#         # Notify players
#         await self.broadcast_game_over()
#         # Close player connections if necessary
#         for player in self.players.values():
#             await player.disconnect()
#     async def join(self, player: PlayerServer):
#         if len(self.players) >= self._room_size:
#             raise FullGameRoomException("Room is full")
#         self.players[player.id] = player
#         self._logger.info(f"Player {player.id} joined room {self.id}")
#         await self.broadcast_room_update()
#         if len(self.players) >= 2 and not self.active:
#             self._logger.info(f"Enough players in room {self.id}. Starting the game.")
#             asyncio.create_task(self.activate())

#     async def leave(self, player_id: str):
#         if player_id in self.players:
#             del self.players[player_id]
#             self._logger.info(f"Player {player_id} left room {self.id}")
#             await self.broadcast_room_update()

#     async def activate(self):
#         self.active = True
#         try:
#             self._logger.info(f"Activating room {self.id}")
#             dealer_key = -1
#             while True:
#                 await self.remove_inactive_players()
#                 if len(self.players) < 2:
#                     raise GameError("Not enough players to continue")
#                 dealer_key = (dealer_key + 1) % len(self.players)
#                 dealer_id = list(self.players.keys())[dealer_key]
#                 game = self._game_factory.create_game(list(self.players.values()))
#                 game.event_dispatcher.subscribe(self)
#                 await game.play_hand(dealer_id)
#                 game.event_dispatcher.unsubscribe(self)
#         except GameError as e:
#             self._logger.error(f"Game error in room {self.id}: {e}")
#         finally:
#             self._logger.info(f"Deactivating room {self.id}")
#             self.active = False
#             await self.broadcast_game_over()

#     async def remove_inactive_players(self):
#         # Implement logic to remove inactive players
#         # For example, based on last_pong timestamp
#         current_time = asyncio.get_event_loop().time()
#         inactive_players = [
#             player_id for player_id, player in self.players.items()
#             if hasattr(player, 'last_pong') and (current_time - player.last_pong > 60)  # 60 seconds timeout
#         ]

#         for player_id in inactive_players:
#             self._logger.info(f"Removing inactive player {player_id} from room {self.id}")
#             await self.leave(player_id)

#     async def broadcast_room_update(self):
#         # Implement broadcasting room updates to all players
#         message = {
#             "message_type": "room-update",
#             "event": "update",
#             "player_ids": list(self.players.keys()),
#             "players": {player_id: player.dto() for player_id, player in self.players.items()},
#         }
#         await self.broadcast(message)

#     async def broadcast_game_over(self):
#         message = {
#             "message_type": "game-update",
#             "event": "game-over",
#         }
#         await self.broadcast(message)

#     async def broadcast(self, message):
#         # Send the message to all players in the room
#         await asyncio.gather(
#             *(player.send_message(message) for player in self.players.values())
#         )

#     async def game_event(self, event, event_data):
#         # Handle game events and send messages to players
#         event_message = {"message_type": "game-update", **event_data}
#         if "target" in event_data:
#             player_id = event_data["target"]
#             player = self.players.get(player_id)
#             if player:
#                 await player.send_message(event_message)
#         else:
#             await self.broadcast(event_message)


# class GameRoomFactory:
#     def __init__(self, game_factory, room_size: int = 10, logger: Optional[logging.Logger] = None):
#         self._game_factory = game_factory
#         self._room_size = room_size
#         self._logger = logger or logging.getLogger(__name__)

#     def create_room(self, id: str, private: bool = False, logger: Optional[logging.Logger] = None) -> GameRoom:
#         room_logger = logger or self._logger
#         room = GameRoom(id=id, game_factory=self._game_factory, logger=room_logger)
#         room.private = private
#         room._room_size = self._room_size
#         return room
