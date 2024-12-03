# consumer.py

import uuid
import logging
import re
import json
from channels.generic.websocket import AsyncJsonWebsocketConsumer
import time
import redis
import asyncio
from .Services.Logic.poker_game_holdem import HoldemPokerGameFactory
from .Services.Logic.player import Player
import queue
from asgiref.sync import async_to_sync
from .Services.Logic.player_server import PlayerServer  # Adjust the path based on your project structure


from redis import Redis


logger = logging.getLogger(__name__)
from asgiref.sync import async_to_sync

class SyncChannel:
    def __init__(self, channel_layer, channel_name, message_queue):
        self.channel_layer = channel_layer
        self.channel_name = channel_name
        self.message_queue = message_queue

    def send_message(self, message):
        async_to_sync(self.channel_layer.send)(
            self.channel_name,
            {
                "type": "game_message",
                "message": message,
            }
        )

    def recv_message(self, timeout_epoch=None):
        timeout = None
        if timeout_epoch is not None:
            timeout = max(0, timeout_epoch - time.time())

        try:
            message = self.message_queue.get(timeout=timeout)
            return message
        except queue.Empty:
            raise Exception("MessageTimeout")

class PokerGameConsumer(AsyncJsonWebsocketConsumer):
    # Class-level variable to maintain room states
    rooms = {}
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.player_queues = {}

        self.active = False
        self._logger = logger
        self.players = {}
        self.player_channels = {}
        self.room_id = None
        self.room_group_name = None
    async def start_game(self, event):
        room = PokerGameConsumer.rooms.get(self.room_group_name)
        if not room:
            self._logger.error(f"Room {self.room_id} not found.")
            return

        if not room.get('active', False):
            room['active'] = True
            self._logger.info(f"Starting game in room {self.room_id}")
            await self.activate_game()
        else:
            self._logger.info(f"Game already active in room {self.room_id}")
    async def broadcast(self, message):
        await self.channel_layer.group_send(
            self.room_group_name,
            {
            "type": "game_message",
            "message": message,
            }
        )
    async def activate_game(self):
        try:
            self._logger.info(f"Activating game in room {self.room_id}")
            dealer_key = -1
            while True:
                try:
                    # Remove inactive players
                    await self.remove_inactive_players()
                    # Send ping and wait for pongs
                    await self.send_ping()
                    # Wait for a while
                    await asyncio.sleep(5)  # Adjust as necessary
                # Remove inactive players again
                    await self.remove_inactive_players()
                    
                    room = PokerGameConsumer.rooms.get(self.room_group_name)
                    if room is None:
                        raise Exception("Room not found")
                    players_info = room['players']


                    players_list = list(players_info.keys())
                    if len(players_list) < 2:
                        raise Exception("At least two players needed to start a new game")

                    dealer_key = (dealer_key + 1) % len(players_list)
                    dealer_id = players_list[dealer_key]

                # Create game instance and start the game
                # Implement your game logic here
                # For example:
                    await self.play_hand(dealer_id, players_info)

                except Exception as e:
                    self._logger.error(f"Game error in room {self.room_id}: {e}")
                    break

        finally:
            self._logger.info(f"Deactivating game in room {self.room_id}")
            room = PokerGameConsumer.rooms.get(self.room_group_name)
            if room:
                room['active'] = False  # Reset the active flag

        # Notify clients that the game is over
            await self.broadcast({
            "message_type": "game-update",
            "event": "game-over",
            })
    async def connect(self):
        logger.info("WebSocket connection initiated.")
        self.session = self.scope['session']
        self.session_id = str(uuid.uuid4())
        self.session['session_id'] = self.session_id

        # Extract room_id and sanitize
        self.room_id = self.session.get('room-id', 'default-room')
        sanitized_room_id = re.sub(r'[^a-zA-Z0-9\-_\.]', '_', self.room_id)
        self.room_group_name = f"game_room_{sanitized_room_id}"  # Use consistent group name
        self.room_id = self.room_group_name  # Ensure room_id matches group name

        logger.info(f"Connecting to group: {self.room_group_name}")

        # Session data validation
        if "player-id" not in self.session:
            logger.error("Player session data missing. Closing connection.")
            await self.close()
            return

        # Player info
        self.player_id = self.session["player-id"]
        self.player_name = self.session.get("player-name", "Anonymous")
        self.player_money = self.session.get("player-money", "0")

        logger.debug(f"Player Info - ID: {self.player_id}, Name: {self.player_name}, Money: {self.player_money}")

        # Add the player to the WebSocket group
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        logger.debug(f"Player {self.player_id} added to group {self.room_group_name}")

        # Accept the WebSocket connection
        await self.accept()
        logger.info(f"WebSocket connection accepted for player {self.player_id}")

        # Initialize room if it doesn't exist
        if self.room_group_name not in PokerGameConsumer.rooms:
            PokerGameConsumer.rooms[self.room_group_name] = {
                'player_channels': {},
                'players': {},
                'active': False,  # Add this line

            }

        # Add player to room state
        room = PokerGameConsumer.rooms[self.room_group_name]
        room['player_channels'][self.player_id] = self.channel_name
        room['players'][self.player_id] = {
            'player_id': self.player_id,
            'player_name': self.player_name,
            'player_money': self.player_money,
            'session_id': self.session_id,
            'last_pong': time.time(),
        }
        
        redis_client = redis.Redis()
        redis_client.publish("room_updates", json.dumps({
        'room_id': self.room_group_name,
        'action': 'player_joined',
        'player_id': self.player_id,
        'player_info': room['players'][self.player_id],
        }))
        
        # Broadcast room update
        await self.broadcast_room_update()

        # Send 'connect' message only to the connecting client
        await self.send_json({
            "message_type": "connect",
            "player_id": self.player_id,
            "player_name": self.player_name,
            "player_money": self.player_money,
        })
        logger.debug(f"Sent 'connect' message to player {self.player_id}")

        logger.info(f"Player {self.player_id} ({self.player_name}) connected to room {self.room_id}.")

    async def disconnect(self, close_code):
        logger.info(f"WebSocket disconnect initiated for player {self.player_id} with close code {close_code}")

        # Remove player from the room state
        room = PokerGameConsumer.rooms.get(self.room_group_name)
        if room:
            room['player_channels'].pop(self.player_id, None)
            room['players'].pop(self.player_id, None)
            # Broadcast room update
            await self.broadcast_room_update()
            # If room is empty, remove it
            if not room['players']:
                PokerGameConsumer.rooms.pop(self.room_group_name)

        # Remove player from the WebSocket group
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)
        logger.debug(f"Player {self.player_id} removed from group {self.room_group_name}")

        logger.info(f"Player {self.player_id} disconnected and removed from room {self.room_id}.")

    async def receive_json(self, content):
        """
        Handle messages received from the WebSocket client.
        """
        message_type = content.get("message_type")
        logger.debug(f"Received message from player {self.player_id}: {content}")
        if self.player_id in self.player_queues:
            self.player_queues[self.player_id].put(content)

        if message_type == 'pong':
            await self.handle_pong()
        elif message_type == 'bet':
        # Handle bet message
            await self.handle_player_action({
            'player_id': self.player_id,
            'message': content,
        })
        else:
            # Handle other message types as needed
            pass

    async def handle_pong(self):
        room = PokerGameConsumer.rooms.get(self.room_group_name)
        if room and self.player_id in room['players']:
            room['players'][self.player_id]['last_pong'] = time.time()
            logger.debug(f"Received pong from player {self.player_id}")

    async def broadcast_room_update(self):
        room = PokerGameConsumer.rooms.get(self.room_group_name)
        if room:
            message = {
                "message_type": "room-update",
                "event": "update",
                "player_ids": list(room['player_channels'].keys()),
                "players": room['players'],
            }
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "game_message",
                    "message": message,
                }
            )

    async def game_message(self, event):
        """
        Send messages to WebSocket client.
        """
        
        try:
            await self.send_json(event["message"])
            logger.debug(f"Sent game message to player {self.player_id}: {event['message']}")
        except Exception as e:
            logger.error(f"Error sending game message to player {self.player_id}: {str(e)}")

    
    async def remove_inactive_players(self):
        room = PokerGameConsumer.rooms.get(self.room_group_name)
        if room is None:
            return
        current_time = time.time()
        inactive_players = []
        for player_id, player_info in room['players'].items():
            last_pong = player_info.get('last_pong', 0)
            if current_time - last_pong > 60:  # Adjust timeout as needed
                inactive_players.append(player_id)

        for player_id in inactive_players:
            self._logger.info(f"Removing inactive player {player_id}")
            if player_id in room['player_channels']:
                del room['player_channels'][player_id]
            if player_id in room['players']:
                del room['players'][player_id]
        # Notify others about player leaving
        await self.broadcast_room_update()
    async def play_hand(self, dealer_id, players_info):
    # Convert players_info to Player objects
        players = []
        for player_id, player_data in players_info.items():
            channel_name = PokerGameConsumer.rooms[self.room_group_name]['player_channels'].get(player_id)
            if not channel_name:
                self._logger.error(f"Channel not found for player {player_id}")
                continue
            if player_id not in self.player_queues:
                self.player_queues[player_id] = queue.Queue()
            channel = SyncChannel(
                channel_layer=self.channel_layer,
                channel_name=channel_name,
                message_queue=self.player_queues[player_id]
            )

            player = PlayerServer(
                channel=channel,
                logger=logger,
                id=player_id,
                name=player_data['player_name'],
                money=float(player_data['player_money'])
            )
            players.append(player)

    # Create game factory
        game_factory = HoldemPokerGameFactory(
            big_blind=50,
            small_blind=25,
            logger=logger
        )

    # Create game instance
        game = game_factory.create_game(players)

    # Start the game
    # Since the game logic is synchronous and uses gevent, we need to run it in a thread or executor
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, game.play_hand, dealer_id)

    async def send_ping(self):
    # Send ping to all players
        await self.broadcast({"message_type": "ping"})
        self._logger.debug(f"Sent ping to group {self.room_group_name}")
    async def handle_player_action(self, event):
        player_id = event['player_id']
        message = event['message']
    # Process the player's message
        message_type = message.get('message_type')
        if message_type == 'bet':
        # Pass the bet to the game logic
        # You might need to implement a way to communicate this to the game instance
            pass
        else:
        # Other message types
            pass