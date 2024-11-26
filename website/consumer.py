import os
import uuid
import redis
from channels.generic.websocket import AsyncWebsocketConsumer
import json
import logging
import asyncio

from website.Services.Logic.channel import ChannelError, MessageFormatError, MessageTimeout
from website.Services.Logic.player import Player
from website.Services.Logic.player_client import PlayerClientConnector

# Redis configuration
redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379")
redis_client = redis.from_url(redis_url)

logger = logging.getLogger(__name__)

class PokerGameConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.connection_channel = self.scope['url_route']['kwargs']['connection_channel']

        # Access session data
        session = self.scope['session']

        if "player-id" not in session:
            await self.send_json({"message_type": "error", "error": "Unrecognized user"})
            await self.close()
            return

        self.session_id = str(uuid.uuid4())

        self.player_id = session["player-id"]
        self.player_name = session["player-name"]
        self.player_money = session["player-money"]
        self.room_id = session.get("room-id")

        self.player_connector = PlayerClientConnector(redis_client, self.connection_channel, logger)

        try:
            self.server_channel = self.player_connector.connect(
                player=Player(
                    id=self.player_id,
                    name=self.player_name,
                    money=self.player_money
                ),
                session_id=self.session_id,
                room_id=self.room_id
            )

        except (ChannelError, MessageFormatError, MessageTimeout) as e:
            logger.error(f"Unable to connect player {self.player_id} to the poker server: {e.args[0]}")
            await self.close()
            return

        else:
            await self.accept()

            # Forwarding connection to the client
            await self.send_json(self.server_channel.connection_message)

            # Start listening to messages from server_channel
            self.receive_task = asyncio.create_task(self.receive_from_server())

    async def disconnect(self, close_code):
        # Clean up tasks and channels
        if hasattr(self, 'receive_task'):
            self.receive_task.cancel()
        try:
            self.server_channel.send_message({"message_type": "disconnect"})
        except:
            pass
        finally:
            self.server_channel.close()
        logger.info(f"Player {self.player_id} connection closed")

    async def receive(self, text_data):
        # Receive message from WebSocket and send to server_channel
        try:
            message = json.loads(text_data)
            self.server_channel.send_message(message)
        except json.JSONDecodeError:
            logger.error("Invalid JSON received from client")

    async def receive_from_server(self):
        # Receive messages from server_channel and send to WebSocket client
        try:
            while True:
                message = self.server_channel.recv_message()
                if "message_type" in message and message["message_type"] == "disconnect":
                    raise ChannelError
                await self.send_json(message)
        except (ChannelError, MessageFormatError):
            pass
        finally:
            await self.close()

    async def send_json(self, content):
        # Utility function to send JSON to the WebSocket client
        await self.send(text_data=json.dumps(content))
