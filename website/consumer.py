# consumer.py

import uuid
import logging
import re
import json
from channels.generic.websocket import AsyncJsonWebsocketConsumer
import time

logger = logging.getLogger(__name__)

class PokerGameConsumer(AsyncJsonWebsocketConsumer):
    # Class-level variable to maintain room states
    rooms = {}

    async def connect(self):
        logger.info("WebSocket connection initiated.")
        self.session = self.scope['session']
        self.session_id = str(uuid.uuid4())
        self.session['session_id'] = self.session_id

        # Extract room_id and sanitize
        self.room_id = self.session.get('room-id', 'default-room')
        sanitized_room_id = re.sub(r'[^a-zA-Z0-9\-_\.]', '_', self.room_id)
        self.room_group_name = f"game_room_{sanitized_room_id}"  # Use consistent group name

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

        if message_type == 'pong':
            await self.handle_pong()
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
