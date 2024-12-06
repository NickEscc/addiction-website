# # website/Services/Logic/game_server.py

# import logging
# import asyncio
# from typing import List, Optional
# from uuid import uuid4
# from .player_server import PlayerServer
# from .game_room import GameRoomFactory, GameRoom, FullGameRoomException

# class ConnectedPlayer:
#     def __init__(self, player: PlayerServer, room_id: Optional[str] = None):
#         self.player = player
#         self.room_id = room_id

# class GameServer:
#     def __init__(self, room_factory: GameRoomFactory, logger: Optional[logging.Logger] = None):
#         self.room_factory = room_factory
#         self.logger = logger or logging.getLogger(__name__)
#         self._rooms: List[GameRoom] = []
#         self._lobby_lock = asyncio.Lock()
#         self.player_queue = asyncio.Queue()
#         self._running = True  # Flag to control the server loop

#     async def new_players(self):
#         while self._running:
#             connected_player = await self.player_queue.get()
#             yield connected_player

#     def add_new_player(self, player: PlayerServer, room_id: Optional[str] = None):
#         connected_player = ConnectedPlayer(player=player, room_id=room_id)
#         self.player_queue.put_nowait(connected_player)

#     async def _join_room(self, connected_player: ConnectedPlayer) -> GameRoom:
#         async with self._lobby_lock:
#             if connected_player.room_id:
#                 room = await self._join_private_room(connected_player.player, connected_player.room_id)
#             else:
#                 room = await self._join_any_public_room(connected_player.player)
#             return room

#     async def _join_private_room(self, player: PlayerServer, room_id: str) -> GameRoom:
#         room = next((r for r in self._rooms if r.id == room_id), None)
#         if not room:
#             room = self.room_factory.create_room(id=room_id, private=True)
#             self._rooms.append(room)
#         await room.join(player)
#         return room

#     async def _join_any_public_room(self, player: PlayerServer) -> GameRoom:
#         for room in self._rooms:
#             if not room.private and len(room.players) < room._room_size:
#                 try:
#                     await room.join(player)
#                     return room
#                 except FullGameRoomException:
#                     continue
#         room_id = str(uuid4())
#         room = self.room_factory.create_room(id=room_id, private=False)
#         await room.join(player)
#         self._rooms.append(room)
#         return room

#     async def start(self):
#         self.logger.info(f"{self} running")
#         async for connected_player in self.new_players():
#             self.logger.info(f"{self}: {connected_player.player.id} connected")
#             try:
#                 room = await self._join_room(connected_player)
#                 self.logger.info(f"Player {connected_player.player.id} joined room {room.id}")
#                 if not room.active:
#                     asyncio.create_task(room.activate())
#             except Exception as e:
#                 self.logger.exception(f"{self}: bad connection - {str(e)}")

#     async def stop(self):
#         # Stop accepting new players and close existing rooms
#         self._running = False
#         self.logger.info("Game server is shutting down.")
#         # Wait until all current players are processed
#         while not self.player_queue.empty():
#             await asyncio.sleep(0.1)
#         # Close all rooms
#         for room in self._rooms:
#             await room.deactivate()
#         self.logger.info("Game server has been shut down.")
