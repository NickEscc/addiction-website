import logging
import threading
from typing import List, Generator, Dict
from uuid import uuid4

import gevent

from .player_server import PlayerServer
from .game_room import FullGameRoomException, GameRoom, GameRoomFactory


class ConnectedPlayer:
    def __init__(self, player: PlayerServer, room_id: str = None):
        self.player: PlayerServer = player
        self.room_id: str = room_id


class GameServer:
    def __init__(self, room_factory: GameRoomFactory, logger=None):
        self.room_factory = room_factory  # Initialize _room_factory attribute
        self.logger = logger or logging.getLogger(__name__)  # Initialize _logger
        self.active_games = set()  # Set to track active game rooms
        self._rooms: List[GameRoom] = []  # Initialize _rooms as an empty list
        self._lobby_lock = threading.Lock()  # Initialize _lobby_lock

    def __str__(self):
        return "GameServer"

    def new_players(self) -> Generator[ConnectedPlayer, None, None]:
        raise NotImplementedError

    def __get_room(self, room_id: str) -> GameRoom:
        try:
            return next(room for room in self._rooms if room.id == room_id)
        except StopIteration:
            # Create a new private room since it's specified as private=True
            room = self._room_factory.create_room(id=room_id, private=True, logger=self._logger)
            self._rooms.append(room)
            return room

    def _join_private_room(self, player: PlayerServer, room_id: str) -> GameRoom:
        with self._lobby_lock:
            room = self.__get_room(room_id)
            room.join(player)
            return room

    def _join_any_public_room(self, player: PlayerServer) -> GameRoom:
        with self._lobby_lock:
            # Adding player to the first non-full public room
            for room in self._rooms:
                if not room.private:
                    try:
                        room.join(player)
                        return room
                    except FullGameRoomException:
                        pass

            # All rooms are full: creating new room
            room_id = str(uuid4())
            room = self._room_factory.create_room(id=room_id, private=False, logger=self._logger)
            room.join(player)
            self._rooms.append(room)
            return room

    def _join_room(self, player: ConnectedPlayer) -> GameRoom:
        if player.room_id is None:
            self._logger.info(f"Player {player.player.id}: joining public room")
            return self._join_any_public_room(player.player)
        else:
            self._logger.info(f"Player {player.player.id}: joining private room {player.room_id}")
            return self._join_private_room(player.player, player.room_id)

    def start(self):
        self._logger.info(f"{self} running")
        self.on_start()
        try:
            for player in self.new_players():
                # Player successfully connected: joining the lobby
                self._logger.info(f"{self}: {player.player} connected")
                try:
                    room = self._join_room(player)
                    self._logger.info(f"Room: {room.id}")
                    if not room.active:
                        room.active = True
                        gevent.spawn(room.activate)
                except Exception as e:
                    # Close bad connections and ignore the connection
                    self._logger.exception(f"{self}: bad connection - {str(e)}")
                    pass
        finally:
            self._logger.info(f"{self} terminating")
            self.on_shutdown()

    def on_start(self):
        pass

    def on_shutdown(self):
        pass
