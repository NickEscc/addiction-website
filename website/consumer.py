import uuid
import redis
import logging
import re
import json
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.conf import settings

from asgiref.sync import sync_to_async

from .Services.texasholdem_poker_service import main as poker_service_main

logger = logging.getLogger(__name__)

class PokerGameConsumer(AsyncJsonWebsocketConsumer):

    async def connect(self):
        
        logger.info("WebSocket connection initiated.")
        self.connection_channel = self.scope["url_route"]["kwargs"]["connection_channel"]
        sanitized_channel = re.sub(r'[^a-zA-Z0-9\-_\.]', '_', self.connection_channel)
        logger.debug(f"Received connection_channel: {self.connection_channel}")

        # Get the room_id from the session
        self.session = self.scope['session']
        self.room_id = self.session.get('room-id', 'default-room')
        sanitized_room_id = re.sub(r'[^a-zA-Z0-9\-_\.]', '_', self.room_id)
        self.group_name = f"texas_holdem_{sanitized_room_id}"

        logger.info(f"Connecting to group: {self.group_name}")

        # Connect to Redis
        redis_url = "redis://localhost:6379"
        self.redis_client = redis.from_url(redis_url)
        logger.info(f"Connected to Redis at {redis_url}")

        # Session data
        if "player-id" not in self.session:
            logger.error("Player session data missing.")
            await self.close()
            return

        # Player info
        self.player_id = self.session["player-id"]
        self.player_name = self.session["player-name"]
        self.player_money = self.session["player-money"]

        # Add the player to the group
        await self.channel_layer.group_add(self.group_name, self.channel_name)

        # Accept the connection
        await self.accept()

        # Save player info in Redis
        await self.add_player_to_room()

        # Send 'connect' message only to the connecting client
        await self.send_json({
            "message_type": "connect",
            "player_id": self.player_id,
            "player_name": self.player_name,
            "player_money": self.player_money,
        })

        # Send the list of current players to the new client
        players_in_room = await self.get_players_in_room()
        await self.send_json({
            "message_type": "room-update",
            "event": "initial",
            "players": players_in_room,
        })

        # Notify others in the group about the new player
        await self.channel_layer.group_send(
            self.group_name,
            {
                "type": "game_message",
                "message": {
                    "message_type": "player-added",
                    "player_id": self.player_id,
                    "player_name": self.player_name,
                    "player_money": self.player_money,
                },
            },
        )

        logger.info(f"Player {self.player_id} ({self.player_name}) connected.")

    
    
    async def get_players_in_room(self):
        room_players_key = f"room:{self.room_id}:players"

        # Retrieve the set of player IDs from Redis asynchronously
        player_ids = await sync_to_async(self.redis_client.smembers)(room_players_key)

        # Decode the player IDs (Redis returns bytes)
        player_ids = [pid.decode('utf-8') for pid in player_ids]

        players = []
        for player_id in player_ids:
            player_key = f"player:{player_id}"
            player_info = await sync_to_async(self.redis_client.hgetall)(player_key)
            if player_info:
                # Decode the player_info keys and values
                player_info = {k.decode('utf-8'): v.decode('utf-8') for k, v in player_info.items()}
                players.append({
                    "player_id": player_info.get("player_id"),
                    "player_name": player_info.get("player_name"),
                    "player_money": player_info.get("player_money"),
                })

        return players

    
    async def add_player_to_room(self):
        room_players_key = f"room:{self.room_id}:players"
        player_key = f"player:{self.player_id}"

        # Add player ID to the room's player set
        await sync_to_async(self.redis_client.sadd)(room_players_key, self.player_id)

        # Store player details in a hash
        await sync_to_async(self.redis_client.hset)(player_key, mapping={
            "player_id": self.player_id,
            "player_name": self.player_name,
            "player_money": self.player_money,
        })

    async def disconnect(self, close_code):
        # Remove player from the group
        await self.channel_layer.group_discard(self.group_name, self.channel_name)
        await self.remove_player_from_room()


        # Notify group about player disconnection
        await self.channel_layer.group_send(
            self.group_name,
            {
                "type": "game_message",
                "message": {
                    "message_type": "disconnect",
                    "player_id": self.player_id,
                },
            },
        )

        logger.info(f"Player {self.player_id} disconnected.")


    async def remove_player_from_room(self):
        room_players_key = f"room:{self.room_id}:players"
        player_key = f"player:{self.player_id}"

        # Remove player ID from the room's player set
        await sync_to_async(self.redis_client.srem)(room_players_key, self.player_id)

        # Delete the player's hash
        await sync_to_async(self.redis_client.delete)(player_key)
        
    async def receive_json(self, content):
        """
        Handle messages received from the WebSocket client.
        """
        message_type = content.get("message_type")

        if message_type == "bet":
            try:
                # Relay the message to Redis
                self.redis_client.publish(self.group_name, json.dumps(content))
                logger.info(f"Player {self.player_id} placed a bet: {content}")
            except Exception as e:
                logger.error(f"Error handling bet message: {str(e)}")
                await self.send_json({"message_type": "error", "error": str(e)})

        elif message_type == "start_game":
            try:
                # Example of interacting with the poker service main logic
                poker_service_main()
                logger.info("Texas Hold'em Poker game started.")
                await self.send_json(
                    {"message_type": "info", "message": "Game started successfully."}
                )
            except Exception as e:
                logger.error(f"Error starting game: {str(e)}")
                await self.send_json({"message_type": "error", "error": str(e)})

    async def game_message(self, event):
        """
        Send messages to WebSocket client.
        """
        try:
            await self.send_json(event["message"])
        except Exception as e:
            logger.error(f"Error sending game message: {str(e)}")
