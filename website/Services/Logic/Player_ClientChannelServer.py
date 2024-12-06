# website/Services/logic/Player_ClientChannelServer.py

import logging
import asyncio
from typing import Optional, Any
from .PokerGame import Player

class ChannelError(Exception):
    pass

class MessageTimeout(Exception):
    pass

class MessageFormatError(Exception):
    def __init__(self, attribute=None, desc=None, expected=None, found=None):
        message = "Invalid message received."
        if attribute:
            message += f" Invalid message attribute {attribute}."
            if expected is not None and found is not None:
                message += f" '{expected}' expected, found '{found}'."
        if desc:
            message += " " + desc
        super().__init__(message)

    @staticmethod
    def validate_message_type(message, expected):
        if "message_type" not in message:
            raise MessageFormatError(attribute="message_type", desc="Attribute is missing")
        elif message["message_type"] == "error":
            if "error" in message:
                raise MessageFormatError(desc=f"Error received from the remote host: '{message['error']}'")
            else:
                raise MessageFormatError(desc="Unknown error received from the remote host")
        if message["message_type"] != expected:
            raise MessageFormatError(attribute="message_type", expected=expected, found=message["message_type"])

class PlayerServer(Player):
    def __init__(self, id: str, name: str, money: float, channel=None, logger=None):
        super().__init__(id=id, name=name, money=money)
        self._channel = channel
        self._connected = True
        self._logger = logger or logging.getLogger(__name__)
        self.last_active = asyncio.get_event_loop().time()  # Initialize last active time

    @property
    def connected(self) -> bool:
        return self._connected

    async def send_message(self, message: Any):
        if not self._connected or self._channel is None:
            self._logger.error(f"Cannot send message, player {self.id} not connected or channel missing.")
            return

        try:
            await self._channel.send_json(message)
            self._logger.debug(f"Message sent to player {self.id}: {message}")
        except Exception as e:
            self._logger.error(f"Failed to send message to player {self.id}: {e}")
            self._connected = False

    async def recv_message(self, timeout_epoch: Optional[float] = None) -> Any:
        if not self._connected or self._channel is None:
            raise ChannelError("Not connected")
        try:
            if timeout_epoch is not None:
                timeout = max(0, timeout_epoch - asyncio.get_event_loop().time())
                message = await asyncio.wait_for(self._channel.receive_json(), timeout=timeout)
            else:
                message = await self._channel.receive_json()
            self._logger.debug(f"Message received from player {self.id}: {message}")
            # Update last_active time whenever a message is received
            self.last_active = asyncio.get_event_loop().time()
            return message
        except asyncio.TimeoutError:
            self._logger.error(f"Receiving message timed out for player {self.id}")
            raise MessageTimeout("Receiving message timed out.")

    async def disconnect(self):
        if self._connected:
            if self._channel is not None:
                await self.send_message({"message_type": "disconnect"})
            self._connected = False
            self._logger.info(f"Player {self.id} disconnected.")
