# website/Services/consumer.py

import uuid
import logging
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.db import database_sync_to_async
from website.Services.Logic.Player_ClientChannelServer import PlayerServer
from website.Services.Logic.Game_server_instance import get_game_server_instance

logger = logging.getLogger(__name__)

class PokerGameConsumer(AsyncJsonWebsocketConsumer):
    rooms = {}

    async def connect(self):
        logger.info("WebSocket connection initiated.")
        self.player_id = None
        self.session = self.scope['session']
        await self.accept()
        logger.info("WebSocket connection accepted.")

        self.room_id = None
        self.player_server = None
        self.player_name = None
        self.player_money = None
        self.room_group_name = None

    async def disconnect(self, close_code):
        player_id = self.player_id if self.player_id else 'Unknown'
        logger.info(f"WebSocket disconnect initiated for player {player_id} with close code {close_code}")
        if self.room_id:
            self.room_group_name = f"game_room_{self.room_id}"
            await self.remove_player_from_room()
            await self.channel_layer.group_discard(self.room_group_name, self.channel_name)
            logger.debug(f"Player {player_id} removed from group {self.room_group_name}")
            if self.player_server:
                await self.player_server.disconnect()
                logger.info(f"Player {player_id} disconnected and removed from GameServer.")

            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "player_left",
                    "player_id": self.player_id,
                    "player_name": self.player_name,
                }
            )

    async def receive_json(self, content):
        """
        Handle messages received from the WebSocket client.
        """
        message_type = content.get("message_type")
        logger.debug(f"Received message: {content}")

        if message_type == 'join':
            await self.handle_join(content)
        elif message_type == 'pong' and self.player_server:
            await self.player_server.handle_pong()
        elif message_type == 'bet' and self.player_server:
            await self.player_server.receive_bet(content)
        else:
            # Handle other message types as needed
            logger.warning(f"Unhandled message type: {message_type}")

    @database_sync_to_async
    def get_session_value(self, key, default=None):
        return self.session.get(key, default)

    async def handle_join(self, content):
        """
        Handle a join message containing the player's name and room ID.
        """
        name = content.get("name")
        room_id = content.get("room_id")

        if not name or not room_id:
            logger.error("Join message missing name or room_id.")
            await self.send_json({"message_type": "error", "error": "Missing name or room_id."})
            await self.close()
            return

        self.player_name = name
        self.room_id = room_id
        self.room_group_name = f"game_room_{self.room_id}"

        logger.info(f"Player {self.player_name} is joining room {self.room_id}")

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        logger.debug(f"Player {self.player_name} added to group {self.room_group_name}")

        self.player_id = await self.get_session_value('player_id', str(uuid.uuid4()))
        self.player_money = await self.get_session_value('player_money', 1000.0)

        game_server_instance = get_game_server_instance()
        if game_server_instance is None:
            logger.error("Game server instance is not initialized. Closing connection.")
            await self.send_json({"message_type": "error", "error": "Game server is not available."})
            await self.close()
            return

        # Create a PlayerServer instance
        self.player_server = PlayerServer(
            channel=self,
            id=self.player_id,
            name=self.player_name,
            money=self.player_money,
            logger=logger
        )

        # Add the player to the game server
        game_server_instance.add_new_player(self.player_server, room_id=self.room_id)
        logger.info(f"Player {self.player_id} added to GameServer.")

        await self.add_player_to_room()

        await self.send_json({
            "message_type": "join-success",
            "player_id": self.player_id,
            "player_name": self.player_name,
            "player_money": self.player_money,
            "room_id": self.room_id
        })

        await self.send_room_update()

    async def add_player_to_room(self):
        """
        Add the player to the room's player list.
        """
        if self.room_id not in self.rooms:
            self.rooms[self.room_id] = {}

        self.rooms[self.room_id][self.player_id] = {
            "player_id": self.player_id,
            "player_name": self.player_name,
            "player_money": self.player_money
        }
        logger.debug(f"Player {self.player_id} added to room {self.room_id}")

    async def remove_player_from_room(self):
        """
        Remove the player from the room's player list.
        """
        if self.room_id in self.rooms and self.player_id in self.rooms[self.room_id]:
            del self.rooms[self.room_id][self.player_id]
            logger.debug(f"Player {self.player_id} removed from room {self.room_id}")

            # If the room is empty, remove it
            if not self.rooms[self.room_id]:
                del self.rooms[self.room_id]
                logger.debug(f"Room {self.room_id} is now empty and removed.")

    async def send_room_update(self):
        """
        Send the updated list of players to all clients in the room.
        """
        players_in_room = list(self.rooms[self.room_id].values())
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "room_update",
                "players": players_in_room
            }
        )

    async def room_update(self, event):
        """
        Handle room updates by sending the updated player list to the client.
        """
        await self.send_json({"message_type": "room-update", "players": event["players"]})

    async def player_left(self, event):
        """
        Notify clients that a player has left the room.
        """
        await self.send_json({
            "message_type": "player-removed",
            "player_id": event["player_id"],
            "player_name": event["player_name"]
        })

    async def player_joined(self, event):
        """
        This method is kept for compatibility but isn't used in this approach.
        """
        pass  # We handle player join through room_update

    async def send_message(self, message):
        """
        Asynchronously send a message to the WebSocket client.
        """
        try:
            await self.send_json(message)
            logger.debug(f"Sent message to player {self.player_id}: {message}")
        except Exception as e:
            logger.error(f"Error sending message to player {self.player_id}: {str(e)}")
