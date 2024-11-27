import json
import uuid
import redis
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from django.conf import settings

from .Services.texasholdem_poker_service import main as poker_service_main

logger = logging.getLogger(__name__)

class PokerGameConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        logger.info("WebSocket connection initiated.")
        self.connection_channel = self.scope["url_route"]["kwargs"]["connection_channel"]
        sanitized_channel = self.connection_channel.replace(":", "-")

        self.group_name = f"texas-holdem:{self.connection_channel}"
        logger.info(f"Connecting to group: {self.group_name}")

        # Connect to Redis
        redis_url = "redis://localhost:6379"
        self.redis_client = redis.from_url(redis_url)
        logger.info(f"Connected to Redis at {redis_url}")

        # Session data
        self.session = self.scope['session']
        if "player-id" not in self.session:
            logger.error("Player session data missing.")
            await self.close()
            return

        # Add the player to the group
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

        # Player info
        self.player_id = self.session["player-id"]
        self.player_name = self.session["player-name"]
        self.player_money = self.session["player-money"]

        logger.info(f"Player {self.player_id} ({self.player_name}) connected.")

        # Notify group
        await self.channel_layer.group_send(
            self.group_name,
            {
                "type": "game_message",
                "message": {
                    "message_type": "connect",
                    "player_id": self.player_id,
                    "player_name": self.player_name,
                    "player_money": self.player_money,
                },
            },
        )

    async def disconnect(self, close_code):
        # Remove player from the group
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

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
