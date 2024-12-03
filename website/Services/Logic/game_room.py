# website/Services/Logic/game_room.py

import threading
from typing import Dict, List, Optional
import os
import redis 
import time
import logging
import asyncio


import gevent
from redis import Redis

# from website.Services.Logic.channel_redis import ChannelRedis

# from .player_server import PlayerServer
from .poker_game import GameSubscriber, GameError, GameFactory
from asgiref.sync import async_to_sync
from channels.consumer import AsyncConsumer
from channels.layers import get_channel_layer



class GameRoom(AsyncConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.id = kwargs.get('id', 'default-room')
        self.private = kwargs.get('private', False)
        self.active = False
        self._game_factory = kwargs.get('game_factory')
        self._room_size = kwargs.get('room_size', 10)
        self._logger = kwargs.get('logger', logging.getLogger(__name__))
        self.player_channels = {}  # Mapping of player IDs to channel names
        self.players = {}  # Store player info
        self.channel_layer = get_channel_layer()
        self.group_name = f"game_room_{self.id}"
        self.on_game_over = None
        self._event_messages = []
        

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
        self._logger.info(f"Player {player_id} added to GameRoom {self.id}")

        # Notify others about new player
        await self.broadcast_room_update()
        if len(self.players) >= 2 and not self.active:
            self._logger.info(f"Enough players in room {self.id}. Starting the game.")
            asyncio.create_task(self.activate())

    async def remove_player(self, event):
        player_id = event['player_id']
        if player_id in self.player_channels:
            del self.player_channels[player_id]
        if player_id in self.players:
            del self.players[player_id]
        self._logger.info(f"Player {player_id} removed from GameRoom {self.id}")

        # Notify others about player leaving
        await self.broadcast_room_update()

    async def player_message(self, event):
        player_id = event['player_id']
        message = event['message']
        # Process the player's message
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
        # Update last activity timestamp for the player
        if player_id in self.players:
            self.players[player_id]['last_pong'] = time.time()
            self._logger.debug(f"Received pong from player {player_id}")

    async def broadcast(self, message):
        await self.channel_layer.group_send(
            self.group_name,
            {
                "type": "game_message",
                "message": message,
            }
        )

    async def broadcast_room_update(self):
        # Build and send the room update message
        message = {
            "message_type": "room-update",
            "event": "update",
            "player_ids": list(self.player_channels.keys()),
            "players": self.players,
        }
        await self.broadcast(message)

    async def send_ping(self):
        # Send ping to all players
        await self.broadcast({"message_type": "ping"})
        self._logger.debug(f"Sent ping to group {self.group_name}")

    async def pong(self, event):
        player_id = event['player_id']
        await self.handle_pong(player_id)

    async def send_message_to_player(self, player_id, message):
        channel_name = self.player_channels.get(player_id)
        if channel_name:
            await self.channel_layer.send(
                channel_name,
                {
                    "type": "game_message",
                    "message": message,
                }
            )
        else:
            self._logger.warning(f"No channel found for player {player_id}")

    async def game_message(self, event):
        message = event["message"]
        # Handle messages from clients if needed

    async def game_event(self, event, event_data):
        # Handle game events and send messages to players
        event_message = {"message_type": "game-update"}
        event_message.update(event_data)

        if "target" in event_data:
            player_id = event_data["target"]
            await self.send_message_to_player(player_id, event_message)
        else:
            await self.broadcast(event_message)

        if event == "game-over":
            self._event_messages = []
        else:
            self._event_messages.append(event_message)

    async def remove_inactive_players(self):
        # Remove players who haven't responded to pings
        current_time = time.time()
        inactive_players = []
        for player_id, player_info in self.players.items():
            last_pong = player_info.get('last_pong', 0)
            if current_time - last_pong > 60:  # Adjust timeout as needed
                inactive_players.append(player_id)

        for player_id in inactive_players:
            self._logger.info(f"Removing inactive player {player_id}")
            if player_id in self.player_channels:
                del self.player_channels[player_id]
            if player_id in self.players:
                del self.players[player_id]
            # Notify others about player leaving
            await self.broadcast_room_update()

    async def activate(self):
        self.active = True
        try:
            self._logger.info("Activating room {}...".format(self.id))
            dealer_key = -1
            while True:
                try:
                    # Remove inactive players
                    await self.remove_inactive_players()
                    # Send ping and wait for pongs
                    await self.send_ping()
                    # Wait for a while
                    await asyncio.sleep(30)  # Adjust as necessary
                    # Remove inactive players again
                    await self.remove_inactive_players()

                    players = list(self.players.keys())
                    if len(players) < 2:
                        raise GameError("At least two players needed to start a new game")

                    dealer_key = (dealer_key + 1) % len(players)
                    dealer_id = players[dealer_key]

                    # Create game instance and start the game
                    game = self._game_factory.create_game(players)
                    game.event_dispatcher.subscribe(self)
                    await game.play_hand(dealer_id)
                    game.event_dispatcher.unsubscribe(self)

                except GameError:
                    break

        finally:
            self._logger.info("Deactivating room {}...".format(self.id))
            self.active = False
            if hasattr(self, 'on_game_over') and self.on_game_over:
                await self.on_game_over(self.id)