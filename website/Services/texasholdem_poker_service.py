# website/Services/texasholdem_poker_service.py

import logging
import redis
import os
import time
import threading
import json
import django
from asgiref.sync import async_to_sync

from channels.layers import get_channel_layer

# Set the correct Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'addiction.settings')  # Ensure this matches your project name
django.setup()

def main():
    # Configure logging
    logging.basicConfig(level=logging.DEBUG if 'DEBUG' in os.environ else logging.INFO)
    logger = logging.getLogger("TexasHoldemServer")

    # Get the channel layer
    # channel_layer = get_channel_layer()

    # Get Redis URL from environment or use default
    redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379")

    try:
        # Initialize Redis client
        redis_client = redis.from_url(redis_url)
        logger.info("Connected to Redis at %s", redis_url)

        # Start monitoring rooms (if necessary)
        threading.Thread(target=monitor_rooms, args=(redis_client, logger), daemon=True).start()

        # Keep the main thread alive
        while True:
            time.sleep(1)
    except Exception as e:
        logger.error("Error occurred: %s", str(e))

def monitor_rooms(redis_client, logger):
    pubsub = redis_client.pubsub()
    pubsub.subscribe("room_updates")
    logger.debug("Subscribed to 'room_updates' channel.")

    rooms = {}  # Keep track of rooms and their players
    channel_layer = get_channel_layer()

    for message in pubsub.listen():
        if message['type'] != 'message':
            continue

        try:
            data = json.loads(message['data'])
            room_id = data.get('room_id')
            action = data.get('action')
            player_id = data.get('player_id')
            player_info = data.get('player_info', {})

            logger.debug(f"Received room update: room_id={room_id}, action={action}, player_id={player_id}")

            if not room_id or not player_id:
                logger.warning("Received room_update message without room_id or player_id.")
                continue

            if action == "player_joined":
                # Add player to room
                if room_id not in rooms:
                    rooms[room_id] = []
                rooms[room_id].append(player_id)

                # Check if there are at least 2 players
                if len(rooms[room_id]) == 2:
                    # Start the game
                    logger.info(f"Starting game in room {room_id}")
                    # Implement logic to start the game
                    # For example, create a GameRoom instance and call start_game()
                    async_to_sync(channel_layer.group_send)(
                        room_id,
                        {
                            "type": "start_game",
                        }
                    )
            elif action == "player_left":
                # Remove player from room
                if room_id in rooms and player_id in rooms[room_id]:
                    rooms[room_id].remove(player_id)
                    logger.info(f"Player {player_id} left room {room_id}")

        except json.JSONDecodeError:
            logger.error("Failed to decode JSON from room_updates message.")
        except Exception as e:
            logger.error(f"Error processing room_updates message: {str(e)}")

if __name__ == "__main__":
    main()
