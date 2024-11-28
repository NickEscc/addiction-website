# consumer.py

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
        
        # Extract connection_channel from URL route
        self.connection_channel = self.scope["url_route"]["kwargs"].get("connection_channel", "")
        sanitized_channel = re.sub(r'[^a-zA-Z0-9\-_\.]', '_', self.connection_channel)
        logger.debug(f"Received connection_channel: {self.connection_channel} -> Sanitized: {sanitized_channel}")

        # Get the room_id from the session
        self.session = self.scope.get('session', {})
        self.room_id = self.session.get('room-id', 'default-room')
        sanitized_room_id = re.sub(r'[^a-zA-Z0-9\-_\.]', '_', self.room_id)
        self.group_name = f"texas_holdem_{sanitized_room_id}"

        logger.info(f"Connecting to group: {self.group_name}")

        # Connect to Redis
        try:
            redis_url = "redis://localhost:6379"
            self.redis_client = redis.from_url(redis_url)
            logger.info(f"Connected to Redis at {redis_url}")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {str(e)}")
            await self.close()
            return

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
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        logger.debug(f"Player {self.player_id} added to group {self.group_name}")

        # Accept the WebSocket connection
        await self.accept()
        logger.info(f"WebSocket connection accepted for player {self.player_id}")

        # Save player info in Redis
        await self.add_player_to_room()

        # Send 'connect' message only to the connecting client
        await self.send_json({
            "message_type": "connect",
            "player_id": self.player_id,
            "player_name": self.player_name,
            "player_money": self.player_money,
        })
        logger.debug(f"Sent 'connect' message to player {self.player_id}")

        # Broadcast the updated room state to all players in the room
        await self.broadcast_room_update()

        logger.info(f"Player {self.player_id} ({self.player_name}) connected to room {self.room_id}.")

    async def get_players_in_room(self):
        room_players_key = f"room:{self.room_id}:players"

        try:
            # Retrieve the set of player IDs from Redis asynchronously
            player_ids = await sync_to_async(self.redis_client.smembers)(room_players_key)
            # Decode the player IDs (Redis returns bytes)
            player_ids = [pid.decode('utf-8') for pid in player_ids]
            logger.debug(f"Fetched player_ids for room {self.room_id}: {player_ids}")
        except Exception as e:
            logger.error(f"Error fetching players from Redis: {str(e)}")
            player_ids = []

        players_dict = {}
        for player_id in player_ids:
            player_key = f"player:{player_id}"
            try:
                player_info = await sync_to_async(self.redis_client.hgetall)(player_key)
                if player_info:
                    # Decode the player_info keys and values
                    player_info = {k.decode('utf-8'): v.decode('utf-8') for k, v in player_info.items()}
                    players_dict[player_id] = {
                        "player_id": player_info.get("player_id"),
                        "player_name": player_info.get("player_name"),
                        "player_money": player_info.get("player_money"),
                    }
                    logger.debug(f"Fetched player info for {player_id}: {players_dict[player_id]}")
                else:
                    logger.warning(f"No player info found for player_id: {player_id}")
            except Exception as e:
                logger.error(f"Error fetching player {player_id} info from Redis: {str(e)}")

        return {
            "player_ids": player_ids,
            "players": players_dict
        }

    async def add_player_to_room(self):
        room_players_key = f"room:{self.room_id}:players"
        player_key = f"player:{self.player_id}"

        try:
            # Add player ID to the room's player set
            await sync_to_async(self.redis_client.sadd)(room_players_key, self.player_id)
            logger.debug(f"Added player {self.player_id} to Redis set {room_players_key}")
            await sync_to_async(self.redis_client.publish)(
                "room_updates",
                json.dumps({"room_id": self.room_id, "action": "player_joined"})
            )
            # Store player details in a hash
            await sync_to_async(self.redis_client.hset)(player_key, mapping={
                "player_id": self.player_id,
                "player_name": self.player_name,
                "player_money": self.player_money,
            })
            logger.debug(f"Stored player info for {self.player_id} in Redis hash {player_key}")
        except Exception as e:
            logger.error(f"Error adding player {self.player_id} to room {self.room_id}: {str(e)}")

    async def remove_player_from_room(self):
        room_players_key = f"room:{self.room_id}:players"
        player_key = f"player:{self.player_id}"

        try:
            # Remove player ID from the room's player set
            await sync_to_async(self.redis_client.srem)(room_players_key, self.player_id)
            logger.debug(f"Removed player {self.player_id} from Redis set {room_players_key}")

            # Delete the player's hash
            await sync_to_async(self.redis_client.delete)(player_key)
            await sync_to_async(self.redis_client.publish)(
                "room_updates",
                json.dumps({"room_id": self.room_id, "action": "player_left"})
            )
            logger.debug(f"Deleted player info for {self.player_id} from Redis hash {player_key}")
        except Exception as e:
            logger.error(f"Error removing player {self.player_id} from room {self.room_id}: {str(e)}")
          
    async def disconnect(self, close_code):
        logger.info(f"WebSocket disconnect initiated for player {self.player_id} with close code {close_code}")

        # Remove player from the WebSocket group
        await self.channel_layer.group_discard(self.group_name, self.channel_name)
        logger.debug(f"Player {self.player_id} removed from group {self.group_name}")

        # Remove player from the room's player list
        await self.remove_player_from_room()

        # Broadcast the updated room state to all players in the room
        await self.broadcast_room_update()

        logger.info(f"Player {self.player_id} disconnected and removed from room {self.room_id}.")

    async def broadcast_room_update(self):
        # Fetch all players in the room
        room_update = await self.get_players_in_room()

        # Build and send the message to the group
        message = {
            "message_type": "room-update",
            "event": "update",
            **room_update
        }
        logger.debug(f"Broadcasting room update: {json.dumps(message)}")

        try:
            await self.channel_layer.group_send(
                self.group_name,
                {
                    "type": "game_message",
                    "message": message,
                },
            )
            logger.info(f"Broadcasted room update to group {self.group_name}")
        except Exception as e:
            logger.error(f"Error broadcasting room update to group {self.group_name}: {str(e)}")

    async def receive_json(self, content):
        """
        Handle messages received from the WebSocket client.
        """
        message_type = content.get("message_type")
        logger.debug(f"Received message from player {self.player_id}: {content}")

        if message_type == "bet":
            try:
                # Relay the message to Redis (or handle betting logic here)
                self.redis_client.publish(self.group_name, json.dumps(content))
                logger.info(f"Player {self.player_id} placed a bet: {content}")
            except Exception as e:
                logger.error(f"Error handling bet message from player {self.player_id}: {str(e)}")
                await self.send_json({"message_type": "error", "error": str(e)})

        elif message_type == "start_game":
            try:
                poker_service_main()
                logger.info("Texas Hold'em Poker game started.")
                await self.send_json(
                    {"message_type": "info", "message": "Game started successfully."}
                )
            except Exception as e:
                logger.error(f"Error starting game by player {self.player_id}: {str(e)}")
                await self.send_json({"message_type": "error", "error": str(e)})

        elif message_type == "pong":
            # Handle pong response if needed
            logger.debug(f"Received pong from player {self.player_id}")
            # You can implement logic to update last pong time here

    async def game_message(self, event):
        """
        Send messages to WebSocket client.
        """
        try:
            await self.send_json(event["message"])
            logger.debug(f"Sent game message to player {self.player_id}: {event['message']}")
        except Exception as e:
            logger.error(f"Error sending game message to player {self.player_id}: {str(e)}")
