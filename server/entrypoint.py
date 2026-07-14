import asyncio
import json
import websockets
from server.orchestrators.conversation_orchestrator import ConversationOrchestrator

class EntryPoint:
    def __init__(self, host="0.0.0.0", port=8765, event_bus: asyncio.Queue = None, conv_orch: ConversationOrchestrator = None):
        self.host = host
        self.port = port
        self.event_bus = event_bus
        self.active_connections = set()
        self.conv_orch = conv_orch

    async def _handle_connection(self, websocket, path):
        self.active_connections.add(websocket)
        try:
            async for message in websocket:
                await self._handle_inbound(websocket, message)
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            self.active_connections.remove(websocket)

    async def _handle_inbound(self, websocket, message):
        try:
            data = json.loads(message)
            text = data.get("text")
            session_id = data.get("session_id")
            if not text or not session_id:
                return
            response_text = await self.conv_orch.process(text, session_id)
            await websocket.send(json.dumps({"type": "text", "string": response_text}))
        except Exception:
            pass

    async def _listen_to_event_bus(self):
        while True:
            alert = await self.event_bus.get()
            payload = json.dumps(alert)
            if self.active_connections:
                await asyncio.gather(*[c.send(payload) for c in self.active_connections])
            self.event_bus.task_done()

    async def run(self):
        asyncio.create_task(self._listen_to_event_bus())
        async with websockets.serve(self._handle_connection, self.host, self.port):
            await asyncio.Future()
