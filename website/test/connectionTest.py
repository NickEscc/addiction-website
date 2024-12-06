import asyncio
import websockets
import json

async def test_websocket():
    uri = "ws://127.0.0.1:8000/ws/Services/texas-holdem/"
    async with websockets.connect(uri) as websocket:
        # Send a message
        await websocket.send(json.dumps({
            "message_type": "bet",
            "bet": 50
        }))
        print("Message sent: bet 50")

        # Wait for a response
        response = await websocket.recv()
        print(f"Response received: {response}")

asyncio.run(test_websocket())
