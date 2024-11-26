import logging
import redis
import os

from Logic.game_server_redis import GameServerRedis
from Logic.game_room import GameRoomFactory
from Logic.poker_game_traditional import TraditionalPokerGameFactory


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG if 'DEBUG' in os.environ else logging.INFO)
    logger = logging.getLogger()

    # redis_url = os.environ["REDIS_URL"]
    redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379")

    # redis_url = "redis://172.20.10.2:6379"


    server = GameServerRedis(
        redis=redis.from_url(redis_url),
        connection_channel="traditional-poker:lobby",
        room_factory=GameRoomFactory(
            room_size=5,
            game_factory=TraditionalPokerGameFactory(blind=10.0, logger=logger)
        ),
        logger=logger
    )
    server.start()
