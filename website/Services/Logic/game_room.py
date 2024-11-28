# website/Services/Logic/game_room.py

import threading
from typing import Dict, List, Optional
import os
import redis 

import gevent
from redis import Redis

from website.Services.Logic.channel_redis import ChannelRedis

from .player_server import PlayerServer
from .poker_game import GameSubscriber, GameError, GameFactory
from asgiref.sync import async_to_sync


class FullGameRoomException(Exception):
    pass


class DuplicateRoomPlayerException(Exception):
    pass


class UnknownRoomPlayerException(Exception):
    pass


class GameRoomPlayers:
    def __init__(self, room_size: int):
        self._seats: List[Optional[str]] = [None] * room_size
        self._players: Dict[str, PlayerServer] = {}
        self._lock = threading.Lock()

    @property
    def players(self) -> List[PlayerServer]:
        with self._lock:
            return [self._players[player_id] for player_id in self._seats if player_id is not None]

    @property
    def seats(self) -> List[Optional[str]]:
        with self._lock:
            return list(self._seats)

    def get_player(self, player_id: str) -> PlayerServer:
        with self._lock:
            try:
                return self._players[player_id]
            except KeyError:
                raise UnknownRoomPlayerException

    def add_player(self, player: PlayerServer):
        with self._lock:
            if player.id in self._players:
                raise DuplicateRoomPlayerException

            try:
                free_seat = self._seats.index(None)
            except ValueError:
                raise FullGameRoomException
            else:
                self._seats[free_seat] = player.id
                self._players[player.id] = player

    def remove_player(self, player_id: str):
        with self._lock:
            try:
                seat = self._seats.index(player_id)
            except ValueError:
                raise UnknownRoomPlayerException
            else:
                self._seats[seat] = None
                del self._players[player_id]


class GameRoomEventHandler:
    def __init__(self, room_players: GameRoomPlayers, room_id: str, logger, channel_layer=None, group_name=None):
        self._room_players = room_players
        self._room_id = room_id
        self._logger = logger
        self.channel_layer = channel_layer
        self.group_name = group_name

    def room_event(self, event, player_id):
        self._logger.debug(
            "\n" +
            ("-" * 80) + "\n"
            "ROOM: {}\nEVENT: {}\nPLAYER: {}\nSEATS:\n - {}".format(
                self._room_id,
                event,
                player_id,
                "\n - ".join([seat if seat is not None else "(empty seat)" for seat in self._room_players.seats])
            ) + "\n" +
            ("-" * 80) + "\n"
        )
        message = {
            "message_type": "room-update",
            "event": event,
            "room_id": self._room_id,
            "players": {player.id: player.dto() for player in self._room_players.players},
            "player_ids": self._room_players.seats,
            "player_id": player_id
        }
        self.broadcast(message)

    def broadcast(self, message):
        if self.channel_layer and self.group_name:
            async_to_sync(self.channel_layer.group_send)(
                self.group_name,
                {
                    "type": "game_message",
                    "message": message,
                }
            )
        else:
            self._logger.warning("Channel layer or group name not set. Cannot broadcast message.")


class GameRoom(GameSubscriber):
    def __init__(self, id: str, private: bool, game_factory: GameFactory, room_size: int, logger, channel_layer=None, group_name=None):
        self.id = id
        self.private = private
        self.active = False
        self._game_factory = game_factory
        self._room_players = GameRoomPlayers(room_size)
        self.event_handler = GameRoomEventHandler(self._room_players, self.id, logger, channel_layer, group_name)
        self._logger = logger
        self._lock = threading.Lock()
        self.on_game_over = None  # Callback function
        self._event_messages = []  # Initialize event_messages

    def join(self, player):
        with self._lock:
            try:
                self._room_players.add_player(player)
                self.event_handler.room_event("player-added", player.id)
            except DuplicateRoomPlayerException:
                old_player = self._room_players.get_player(player.id)
                old_player.update_channel(player)
                player = old_player
                self.event_handler.room_event("player-rejoined", player.id)

            for event_message in self._event_messages:
                if "target" not in event_message or event_message["target"] == player.id:
                    player.send_message(event_message)

    def leave(self, player_id):
        with self._lock:
            self._leave(player_id)

    def _leave(self, player_id):
        player = self._room_players.get_player(player_id)
        player.disconnect()
        self._room_players.remove_player(player.id)
        self.event_handler.room_event("player-removed", player.id)

    def game_event(self, event, event_data):
        with self._lock:
            # Broadcast the event to the room
            event_message = {"message_type": "game-update"}
            event_message.update(event_data)

            if "target" in event_data:
                player = self._room_players.get_player(event_data["target"])
                player.send_message(event_message)
            else:
                # Broadcasting message
                self.event_handler.broadcast(event_message)

            if event == "game-over":
                self._event_messages = []
            else:
                self._event_messages.append(event_message)

            if event == "dead-player":
                self._leave(event_data["player"]["id"])

    def remove_inactive_players(self):
        def ping_player(player):
            if not player.ping():
                self.leave(player.id)

        gevent.joinall([
            gevent.spawn(ping_player, player)
            for player in self._room_players.players
        ])

    def activate(self):
        self.active = True
        try:
            self._logger.info("Activating room {}...".format(self.id))
            dealer_key = -1
            while True:
                try:
                    self.remove_inactive_players()

                    players = self._room_players.players
                    if len(players) < 2:
                        raise GameError("At least two players needed to start a new game")

                    dealer_key = (dealer_key + 1) % len(players)

                    game = self._game_factory.create_game(players)
                    game.event_dispatcher.subscribe(self.event_handler)
                    game.play_hand(players[dealer_key].id)
                    game.event_dispatcher.unsubscribe(self.event_handler)

                except GameError:
                    break
        finally:
            self._logger.info("Deactivating room {}...".format(self.id))
            self.active = False
            if hasattr(self, 'on_game_over') and self.on_game_over:
                self.on_game_over(self.id)


class GameRoomFactory:
    def __init__(self, room_size: int, game_factory: GameFactory, logger):
        self._room_size: int = room_size
        self._game_factory: GameFactory = game_factory
        self._logger = logger
        self._redis_client = redis.Redis.from_url(os.environ.get("REDIS_URL", "redis://localhost:6379"))

    def create_room(self, id: str, player_ids: List[str], channel_layer, group_name) -> GameRoom:
        game_room = GameRoom(
            id=id,
            private=False,
            game_factory=self._game_factory,
            room_size=self._room_size,
            logger=self._logger,
            channel_layer=channel_layer,
            group_name=group_name
        )

        for player_id in player_ids:
            # Retrieve player data from Redis
            player_key = f"player:{player_id}"
            player_info = self._redis_client.hgetall(player_key)
            if player_info:
                player_info = {k.decode('utf-8'): v.decode('utf-8') for k, v in player_info.items()}
                # Create PlayerServer instance
                player = PlayerServer(
                    channel=ChannelRedis(
                        self._redis_client,
                        f"poker5:player-{player_id}:session-{player_info.get('session_id', 'unknown')}:I",
                        f"poker5:player-{player_id}:session-{player_info.get('session_id', 'unknown')}:O"
                    ),
                    logger=self._logger,
                    id=player_id,
                    name=player_info.get("player_name", "Unknown"),
                    money=float(player_info.get("player_money", 0)),
                )
                game_room.join(player)
            else:
                self._logger.warning(f"No player info found for player_id: {player_id}")

        return game_room  # Fixed to return only game_room
