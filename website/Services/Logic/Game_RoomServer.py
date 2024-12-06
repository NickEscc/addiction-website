# website/Services/logic/Game_RoomServer.py
import logging
import asyncio
from typing import List, Dict, Optional
from uuid import uuid4
from channels.generic.websocket import AsyncConsumer
from .Player_ClientChannelServer import PlayerServer
from .PokerGame import GameFactory, GameSubscriber, GameError, Player, HoldemPokerGameFactory
from .PokerGame import PokerGame, EndGameException, GameError

logger = logging.getLogger(__name__)

class FullGameRoomException(Exception):
    """Exception raised when attempting to join a full game room."""
    pass

class GameRoom(GameSubscriber):
    def __init__(self, id: str, game_factory: GameFactory, logger: Optional[logging.Logger] = None):
        self.id = id
        self.private = False
        self.active = False
        self._game_factory = game_factory
        self._room_size = 10
        self._logger = logger or logging.getLogger(__name__)
        self.players: Dict[str, PlayerServer] = {}
        self.start_votes = set()  # Track which players have pressed "Start Game"

    async def deactivate(self):
        self.active = False
        self._logger.info(f"Room {self.id} is deactivating.")
        await self.broadcast_game_over()
        for player in self.players.values():
            await player.disconnect()

    async def join(self, player: PlayerServer):
        if len(self.players) >= self._room_size:
            raise FullGameRoomException("Room is full")
        self.players[player.id] = player
        self._logger.info(f"Player {player.id} joined room {self.id}")
        await self.broadcast_room_update()
        # Removed automatic game start here. Now requires players to press "Start Game".
        # if len(self.players) >= 2 and not self.active:
        #     self._logger.info(f"Enough players in room {self.id}. Starting the game.")
        #     task = asyncio.create_task(self.activate())
        #     self._logger.debug(f"activate() task created for room {self.id}: {task}")

    async def leave(self, player_id: str):
        if player_id in self.players:
            del self.players[player_id]
            if player_id in self.start_votes:
                self.start_votes.remove(player_id)
            self._logger.info(f"Player {player_id} left room {self.id}")
            await self.broadcast_room_update()

    async def player_ready_for_start(self, player_id: str):
        # Player indicates readiness
        if player_id in self.players:
            self.start_votes.add(player_id)
            self._logger.info(f"Player {player_id} is ready to start in room {self.id}.")
            await self.broadcast_room_update()
            # If all players in the room are ready and we have at least two players, start the game
            if len(self.start_votes) == len(self.players) and len(self.players) >= 2 and not self.active:
                self._logger.info(f"All players ready in room {self.id}. Starting the game.")
                task = asyncio.create_task(self.activate())
                self._logger.debug(f"activate() task created for room {self.id}: {task}")
        else:
            self._logger.warning(f"Unknown player {player_id} tried to ready start in room {self.id}")

    async def activate(self):
        self._logger.info(f"Activating room {self.id}")
        self.active = True
        try:
            dealer_key = -1
            while True:
                self._logger.debug("Starting a new hand.")
                await self.remove_inactive_players()
                if len(self.players) < 2:
                    self._logger.info("Not enough players to continue. Ending the game.")
                    raise GameError("Not enough players to continue")

                dealer_key = (dealer_key + 1) % len(self.players)
                dealer_id = list(self.players.keys())[dealer_key]
                self._logger.info(f"Dealer for this hand is {dealer_id}")

                game = self._game_factory.create_game(list(self.players.values()))
                self._logger.debug(f"Game instance created: {type(game)} with ID {game._id}")
                game.event_dispatcher.subscribe(self)
                self._logger.info("Starting to play hand.")
                await game.play_hand(dealer_id)
                self._logger.info("Hand completed.")
                game.event_dispatcher.unsubscribe(self)

        except GameError as e:
            self._logger.error(f"Game error in room {self.id}: {e}")
        except Exception as e:
            self._logger.exception(f"Unexpected error in room {self.id}: {e}")
        finally:
            self._logger.info(f"Deactivating room {self.id}")
            self.active = False
            # Reset start votes after a round/game ends
            self.start_votes.clear()
            await self.broadcast_game_over()

    async def remove_inactive_players(self):
        current_time = asyncio.get_event_loop().time()
        inactivity_threshold = 120  # seconds
        inactive_players = [
            player_id for player_id, player in self.players.items()
            if (current_time - player.last_active) > inactivity_threshold or not player.connected
        ]
        for player_id in inactive_players:
            self._logger.info(f"Removing inactive player {player_id} from room {self.id}")
            await self.leave(player_id)

    async def broadcast_room_update(self):
        # Indicate if the "Start Game" button should be shown:
        # Show the button if there are at least 2 players and game not active
        can_start = (len(self.players) >= 2 and not self.active)
        ready_players = list(self.start_votes)

        message = {
            "message_type": "room-update",
            "event": "update",
            "player_ids": list(self.players.keys()),
            "players": {player_id: p.dto() for player_id, p in self.players.items()},
            "can_start": can_start,
            "ready_players": ready_players
        }
        await self.broadcast(message)

    async def broadcast_game_over(self):
        message = {
            "message_type": "game-update",
            "event": "game-over",
        }
        await self.broadcast(message)

    async def broadcast(self, message):
        try:
            await asyncio.gather(*(p.send_message(message) for p in self.players.values()), return_exceptions=True)
        except Exception as e:
            self._logger.error(f"Error in broadcast: {e}")

    async def game_event(self, event, event_data):
        # Handle game events and send messages to players
        event_message = {"message_type": "game-update", **event_data}
        if "target" in event_data:
            player_id = event_data["target"]
            player = self.players.get(player_id)
            if player:
                await player.send_message(event_message)
        else:
            await self.broadcast(event_message)


class GameRoomFactory:
    def __init__(self, game_factory: GameFactory, room_size: int = 10, logger: Optional[logging.Logger] = None):
        self._game_factory = game_factory
        self._room_size = room_size
        self._logger = logger or logging.getLogger(__name__)

    def create_room(self, id: str, private: bool = False, logger: Optional[logging.Logger] = None) -> GameRoom:
        room_logger = logger or self._logger
        room = GameRoom(id=id, game_factory=self._game_factory, logger=room_logger)
        room.private = private
        room._room_size = self._room_size
        return room


class ConnectedPlayer:
    def __init__(self, player: PlayerServer, room_id: Optional[str] = None):
        self.player = player
        self.room_id = room_id


class GameServer:
    def __init__(self, room_factory: GameRoomFactory, logger: Optional[logging.Logger] = None):
        self.room_factory = room_factory
        self.logger = logger or logging.getLogger(__name__)
        self._rooms: List[GameRoom] = []
        self._lobby_lock = asyncio.Lock()
        self.player_queue = asyncio.Queue()
        self._running = True

    async def new_players(self):
        while self._running:
            connected_player = await self.player_queue.get()
            yield connected_player

    def add_new_player(self, player: PlayerServer, room_id: Optional[str] = None):
        connected_player = ConnectedPlayer(player=player, room_id=room_id)
        self.player_queue.put_nowait(connected_player)

    async def _join_room(self, connected_player: ConnectedPlayer) -> GameRoom:
        async with self._lobby_lock:
            if connected_player.room_id:
                room = await self._join_private_room(connected_player.player, connected_player.room_id)
            else:
                room = await self._join_any_public_room(connected_player.player)
            return room

    async def _join_private_room(self, player: PlayerServer, room_id: str) -> GameRoom:
        room = next((r for r in self._rooms if r.id == room_id), None)
        if not room:
            room = self.room_factory.create_room(id=room_id, private=True)
            self._rooms.append(room)
        await room.join(player)
        return room

    async def _join_any_public_room(self, player: PlayerServer) -> GameRoom:
        for room in self._rooms:
            if not room.private and len(room.players) < room._room_size:
                try:
                    await room.join(player)
                    return room
                except FullGameRoomException:
                    continue
        room_id = str(uuid4())
        room = self.room_factory.create_room(id=room_id, private=False)
        await room.join(player)
        self._rooms.append(room)
        return room

    async def start(self):
        self.logger.info("Game server running")
        async for connected_player in self.new_players():
            self.logger.info(f"Player {connected_player.player.id} connected")
            try:
                room = await self._join_room(connected_player)
                self.logger.info(f"Player {connected_player.player.id} joined room {room.id}")
            except Exception as e:
                self.logger.exception(f"Bad connection: {str(e)}")

    async def stop(self):
        self._running = False
        self.logger.info("Game server is shutting down.")
        while not self.player_queue.empty():
            await asyncio.sleep(0.1)
        for room in self._rooms:
            await room.deactivate()
        self.logger.info("Game server has been shut down.")


class GameRoomConsumer(AsyncConsumer):
    """
    This consumer won't accept WebSocket connections. It's used to manage players joining/leaving via channel layer.
    """
    async def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.room_id = None
        self.room_group_name = None
        self.player_channels = {}
        self.players = {}
        self._logger = logger

    async def group_add(self):
        self.room_id = self.scope['url_route']['kwargs']['room_id']
        self.room_group_name = f"game_room_{self.room_id}"
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        self._logger.info(f"GameRoomConsumer added to group {self.room_group_name}")

    async def group_discard(self):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)
        self._logger.info(f"GameRoomConsumer removed from group {self.room_group_name}")

    async def add_player(self, event):
        player_id = event['player_id']
        channel_name = event['channel_name']
        player_name = event['player_name']
        player_money = event['player_money']
        session_id = event['session_id']

        self.player_channels[player_id] = channel_name
        self.players[player_id] = {
            'player_id': player_id,
            'player_name': player_name,
            'player_money': player_money,
            'session_id': session_id,
            'last_pong': asyncio.get_event_loop().time(),
        }
        self._logger.info(f"Player {player_id} added to GameRoom {self.room_id}")
        await self.broadcast_room_update()

    async def remove_player(self, event):
        player_id = event['player_id']
        if player_id in self.player_channels:
            del self.player_channels[player_id]
        if player_id in self.players:
            del self.players[player_id]
        self._logger.info(f"Player {player_id} removed from GameRoom {self.room_id}")
        await self.broadcast_room_update()

    async def player_message(self, event):
        player_id = event['player_id']
        message = event['message']
        message_type = message.get('message_type')
        if message_type == 'bet':
            pass
        elif message_type == 'pong':
            await self.handle_pong(player_id)
        else:
            pass

    async def handle_pong(self, player_id):
        if player_id in self.players:
            self.players[player_id]['last_pong'] = asyncio.get_event_loop().time()
            self._logger.debug(f"Received pong from player {player_id}")

    async def broadcast(self, message):
        for channel_name in self.player_channels.values():
            await self.channel_layer.send(
                channel_name,
                {
                    "type": "game_message",
                    "message": message,
                }
            )

    async def broadcast_room_update(self):
        message = {
            "message_type": "room-update",
            "event": "update",
            "player_ids": list(self.player_channels.keys()),
            "players": self.players,
        }
        await self.broadcast(message)

    async def game_message(self, event):
        await self.broadcast(event['message'])

    async def websocket_connect(self, event):
        await self.close()

    async def websocket_receive(self, event):
        pass

    async def websocket_disconnect(self, event):
        pass
