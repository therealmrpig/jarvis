import asyncio
import json
import websockets

class Streamer:
    def __init__(self, uri, session_id, on_message=None):
        self.uri = uri
        self.session_id = session_id
        self.on_message = on_message
        self.websocket = None

    async def connect(self):
        self.websocket = await websockets.connect(self.uri)

    async def send_text(self, text):
        if self.websocket:
            payload = {
                "text": text,
                "session_id": self.session_id
            }
            await self.websocket.send(json.dumps(payload))

    async def listen_loop(self):
        if not self.websocket:
            return
        try:
            async for message in self.websocket:
                if self.on_message:
                    data = json.loads(message)
                    await self.on_message(data)
        except websockets.exceptions.ConnectionClosed:
            pass
        except Exception:
            pass

    async def stop(self):
        if self.websocket:
            await self.websocket.close()
