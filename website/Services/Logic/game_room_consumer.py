# website/services/logic game_room_consumer.py

import logging
from channels.generic.websocket import AsyncConsumer
import time

logger = logging.getLogger(__name__)

class GameRoomConsumer(AsyncConsumer):
    async def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.room_id = None
        self.room_group_name = None
        self.player_channels = {}
        self.players = {}
        self._logger = logger

    async def group_add(self):
        # This method is called when the consumer is instantiated
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
            'last_pong': time.time(),
        }
        self._logger.info(f"Player {player_id} added to GameRoom {self.room_id}")

        # Notify others about new player
        await self.broadcast_room_update()

    async def remove_player(self, event):
        player_id = event['player_id']
        if player_id in self.player_channels:
            del self.player_channels[player_id]
        if player_id in self.players:
            del self.players[player_id]
        self._logger.info(f"Player {player_id} removed from GameRoom {self.room_id}")

        # Notify others about player leaving
        await self.broadcast_room_update()

    async def player_message(self, event):
        player_id = event['player_id']
        message = event['message']
        message_type = message.get('message_type')
        if message_type == 'bet':
            # Handle bet
            pass
        elif message_type == 'pong':
            # Handle pong
            await self.handle_pong(player_id)
        else:
            # Other message types
            pass

    async def handle_pong(self, player_id):
        if player_id in self.players:
            self.players[player_id]['last_pong'] = time.time()
            self._logger.debug(f"Received pong from player {player_id}")

    async def broadcast(self, message):
        # Broadcast message to all players in the room
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
        # Pass the message to clients
        await self.broadcast(event['message'])

    async def websocket_connect(self, event):
        # This method is called when a WebSocket connection is made to this consumer
        # We don't need to accept WebSocket connections, so we can close them
        await self.close()

    async def websocket_receive(self, event):
        # Not needed since we don't accept WebSocket connections
        pass

    async def websocket_disconnect(self, event):
        # Not needed since we don't accept WebSocket connections
        pass
