# # website/Services/Logic/player_server.py

# import logging
# import asyncio
# from typing import Any, Optional
# from .player import Player
# from .channel import MessageTimeout, ChannelError, MessageFormatError
# import json


# class PlayerServer(Player):
#     def __init__(self, channel, logger=None, *args, **kwargs):
#         super().__init__(*args, **kwargs)
#         self._channel = channel  # WebSocket consumer
#         self._connected = True
#         self._logger = logger or logging.getLogger(__name__)

#     def disconnect(self):
#         """Disconnect the client."""
#         if self._connected:
#             asyncio.create_task(self.send_message({"message_type": "disconnect"}))
#             self._connected = False
#             self._logger.info(f"Player {self} disconnected.")

#     @property
#     def connected(self) -> bool:
#         return self._connected

#     async def send_message(self, message: Any):
#         """Asynchronously send a message."""
#         await self._channel.send_json(message)
#         self._logger.debug(f"Message sent to player {self}: {message}")

#     async def recv_message(self, timeout_epoch: Optional[float] = None) -> Any:
#         """Asynchronously receive a message."""
#         try:
#             if timeout_epoch:
#                 timeout = max(0, timeout_epoch - asyncio.get_event_loop().time())
#                 message = await asyncio.wait_for(
#                     self._channel.receive_json(), timeout=timeout
#                 )
#             else:
#                 message = await self._channel.receive_json()
#             self._logger.debug(f"Message received from player {self}: {message}")
#             return message
#         except asyncio.TimeoutError:
#             self._logger.error(f"Receiving message timed out for player {self}")
#             raise MessageTimeout("Receiving message timed out.")

#     async def handle_pong(self):
#         # Implement pong handling
#         pass

#     async def receive_bet(self, message):
#         # Implement bet handling
#         pass
