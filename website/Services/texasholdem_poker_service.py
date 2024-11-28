import logging
import redis
import os
import time
import threading
import json
import django

from website.Services.Logic.game_server_redis import GameServerRedis
from website.Services.Logic.game_room import GameRoomFactory
from website.Services.Logic.poker_game_holdem import HoldemPokerGameFactory
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

# Set the correct Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'addiction.settings')  # Ensure this matches your project name
django.setup()

def main():
    # Configure logging
    logging.basicConfig(level=logging.DEBUG if 'DEBUG' in os.environ else logging.INFO)
    logger = logging.getLogger("TexasHoldemServer")

    # Get the channel layer
    channel_layer = get_channel_layer()

    # Get Redis URL from environment or use default
    redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379")

    try:
        # Initialize Redis client
        redis_client = redis.from_url(redis_url)
        logger.info("Connected to Redis at %s", redis_url)

        # Configure the game server
        server = GameServerRedis(
            redis_client=redis_client,  # Correct argument name based on GameServerRedis
            connection_channel="texas_holdem",  # Ensure this matches the consumer
            room_factory=GameRoomFactory(
                room_size=10,
                game_factory=HoldemPokerGameFactory(
                    big_blind=40.0,
                    small_blind=20.0,
                    logger=logger,
                    game_subscribers=[]
                ),
                logger=logger  # Ensure logger is passed here
            ),
            logger=logger
        )

        # Start the server
        logger.info("Starting Texas Hold'em Poker game server...")

        # Start monitoring rooms in a separate thread
        threading.Thread(target=monitor_rooms, args=(server, redis_client, logger, channel_layer), daemon=True).start()

        # Keep the main thread alive
        while True:
            time.sleep(1)
    except Exception as e:
        logger.error("Error occurred: %s", str(e))

def monitor_rooms(server, redis_client, logger, channel_layer):
    pubsub = redis_client.pubsub()
    pubsub.subscribe("room_updates")
    logger.debug("Subscribed to 'room_updates' channel.")

    for message in pubsub.listen():
        if message['type'] != 'message':
            continue

        try:
            data = json.loads(message['data'])
            room_id = data.get('room_id')
            action = data.get('action')

            logger.debug(f"Received room update: room_id={room_id}, action={action}")

            if not room_id:
                logger.warning("Received room_update message without room_id.")
                continue

            if action == "player_joined":
                # Check the current player count
                room_players_key = f"room:{room_id}:players"
                player_ids = redis_client.smembers(room_players_key)
                player_count = len(player_ids)
                logger.debug(f"Room {room_id} has {player_count} players.")

                if player_count == 2:  # Start game only when exactly 2 players
                    if not server.is_game_running(room_id):
                        player_ids = [pid.decode('utf-8') for pid in player_ids]
                        logger.info(f"Starting game in room {room_id} with players {player_ids}")
                        # Start game in a new thread, passing channel_layer
                        threading.Thread(
                            target=start_game_for_room,
                            args=(server, room_id, player_ids, logger, channel_layer),
                            daemon=True
                        ).start()
                    else:
                        logger.debug(f"Game already running in room {room_id}")
            elif action == "player_left":
                # Optionally, handle player leaving during an active game
                logger.debug(f"Player left room {room_id}")
                # Implement logic if needed

        except json.JSONDecodeError:
            logger.error("Failed to decode JSON from room_updates message.")
        except Exception as e:
            logger.error(f"Error processing room_updates message: {str(e)}")
def start_game_for_room(server, room_id, player_ids, logger, channel_layer):
    group_name = f"texas_holdem_{room_id}"
    try:
        # Create and start the game
        game_room = server.room_factory.create_room(room_id, player_ids, channel_layer, group_name)
        
        # Define a callback to notify the server when the game is over
        def game_over_callback(room_id):
            server.game_over(room_id)

        game_room.on_game_over = game_over_callback

        server.start_game(game_room)

        logger.info(f"Game started in room {room_id} with players {player_ids}")

    except Exception as e:
        logger.error(f"Error starting game in room {room_id}: {str(e)}")
        # Remove from active_games in case of error
        server.active_games.discard(room_id)

if __name__ == "__main__":
    main()
