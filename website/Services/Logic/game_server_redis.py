# # website/Services/Logic/game_server_redis.py

# import time
# from typing import Generator
# import json
# from redis import Redis
# import logging

# # from .game_room import GameRoomFactory
# from .channel_redis import MessageQueue, ChannelRedis, ChannelError, MessageFormatError, MessageTimeout
# from .game_server import GameServer, ConnectedPlayer
# from .player_server import PlayerServer
# import threading
# # from .player_client import PlayerClientConnector


# class GameServerRedis(GameServer):
#     def __init__(
#         self,
#         redis_client: Redis,
#         connection_channel: str,
#         room_factory: GameRoomFactory,
#         logger=None
        
#     ):
#         super().__init__(room_factory, logger)
#         self.redis_client = redis_client  # Changed from self._redis
#         self.connection_channel = connection_channel  # Changed from self._connection_channel
#         self.active_games = set()  # Initialize as a set to track active games

#     def is_game_running(self, room_id):
#         # Implement logic to check if a game is running in the room
#         return room_id in self.active_games

#     def start_game(self, game_room):
#         if game_room.id in self.active_games:
#             self.logger.warning(f"Game already running in room {game_room.id}")
#             return
#         self.active_games.add(game_room.id)
#         self.logger.info(f"Starting game in room {game_room.id}")
#         threading.Thread(target=game_room.activate, daemon=True).start()

#     # def start(self):
#     #     # Subscribe to 'game_server' channel for messages from WebSocket server
#     #     pubsub = self.redis_client.pubsub()
#     #     pubsub.subscribe('game_server')

#     #     while True:
#     #         message = pubsub.get_message(ignore_subscribe_messages=True)
#     #         if message:
#     #             # Handle message from player
#     #             player_message = json.loads(message['data'])
#     #             # Process the message
#     #             self.handle_player_message(player_message)
#     #         time.sleep(0.01)  # Sleep briefly to prevent tight loop

#     def handle_player_message(self, message):
#         player_id = message.get('player_id')
#         # Process the message and send responses back via Redis
#         response = {'message_type': 'update', 'data': '...'}
#         self.redis_client.publish(f'player:{player_id}', json.dumps(response))

#     def _connect_player(self, message) -> ConnectedPlayer:
#         try:
#             timeout_epoch = int(message["timeout_epoch"])
#         except KeyError:
#             raise MessageFormatError(attribute="timeout_epoch", desc="Missing attribute")
#         except ValueError:
#             raise MessageFormatError(attribute="timeout_epoch", desc="Invalid session id")

#         if timeout_epoch < time.time():
#             raise MessageTimeout("Connection timeout")

#         try:
#             session_id = str(message["session_id"])
#         except KeyError:
#             raise MessageFormatError(attribute="session", desc="Missing attribute")
#         except ValueError:
#             raise MessageFormatError(attribute="session", desc="Invalid session id")

#         try:
#             player_id = str(message["player"]["id"])
#         except KeyError:
#             raise MessageFormatError(attribute="player.id", desc="Missing attribute")
#         except ValueError:
#             raise MessageFormatError(attribute="player.id", desc="Invalid player id")

#         try:
#             player_name = str(message["player"]["name"])
#         except KeyError:
#             raise MessageFormatError(attribute="player.name", desc="Missing attribute")
#         except ValueError:
#             raise MessageFormatError(attribute="player.name", desc="Invalid player name")

#         try:
#             player_money = float(message["player"]["money"])
#         except KeyError:
#             raise MessageFormatError(attribute="player.money", desc="Missing attribute")
#         except ValueError:
#             raise MessageFormatError(attribute="player.money",
#                                      desc="'{}' is not a number".format(message["player"]["money"]))

#         try:
#             game_room_id = str(message["room_id"])
#         except KeyError:
#             game_room_id = None
#         except ValueError:
#             raise MessageFormatError(attribute="room_id", desc="Invalid room id")

#         player = PlayerServer(
#             channel=ChannelRedis(
#                 self.redis_client,
#                 f"poker5:player-{player_id}:session-{session_id}:I",
#                 f"poker5:player-{player_id}:session-{session_id}:O"
#             ),
#             logger=self.logger,
#             id=player_id,
#             name=player_name,
#             money=player_money,
#         )

#         # Acknowledging the connection
#         player.send_message({
#             "message_type": "connect",
#             "server_id": self.id,  # Assuming GameServer has an 'id' attribute
#             "player": player.dto()
#         })

#         return ConnectedPlayer(player=player, room_id=game_room_id)

#     def new_players(self) -> Generator[ConnectedPlayer, None, None]:
#         while True:
#             try:
#                 message = self._connection_queue.pop()
#                 yield self._connect_player(message)
#             except (ChannelError, MessageTimeout, MessageFormatError) as e:
#                 self.logger.error("Unable to connect the player: {}".format(e.args[0]))
#                 continue

#     def game_over(self, room_id):
#         if room_id in self.active_games:
#             self.active_games.discard(room_id)
#             self.logger.info(f"Game over in room {room_id}. Room is now available for new games.")
#         else:
#             self.logger.warning(f"Attempted to end game in room {room_id}, but no active game was found.")
