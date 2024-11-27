# website/Services/texasholdem_poker_service.py


import logging
import redis
import os

#python -m website.Services.texasholdem_poker_service
from website.Services.Logic.game_server_redis import GameServerRedis
from website.Services.Logic.game_room import GameRoomFactory
from website.Services.Logic.poker_game_holdem import HoldemPokerGameFactory

def main():
    # Configure logging
    logging.basicConfig(level=logging.DEBUG if 'DEBUG' in os.environ else logging.INFO)
    logger = logging.getLogger("TexasHoldemServer")

    # Get Redis URL from environment or use default
    redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379")

    try:
        # Initialize Redis client
        redis_client = redis.from_url(redis_url)
        logger.info("Connected to Redis at %s", redis_url)

        # Configure the game server
        server = GameServerRedis(
            redis=redis_client,
            connection_channel="texas-holdem-poker:lobby",
            room_factory=GameRoomFactory(
                room_size=10,
                game_factory=HoldemPokerGameFactory(
                    big_blind=40.0,
                    small_blind=20.0,
                    logger=logger,
                    game_subscribers=[]
                )
            ),
            logger=logger
        )

        # Start the server
        logger.info("Starting Texas Hold'em Poker game server...")
        server.start()

    except Exception as e:
        logger.error("Error occurred: %s", str(e))

if __name__ == "__main__":
    main()
