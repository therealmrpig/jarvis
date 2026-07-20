import asyncio
import json
import websockets
from urllib.parse import urlparse, parse_qs

from server.orchestrators.conversation_orchestrator import ConversationOrchestrator
from server.inference.queue import QueueModule
from server_memory.db_handler import DatabaseHandler
from server.tools.executor import ToolExecutor
from server.inference.embeddings import EmbeddingsModule

class EntryPoint:
    def __init__(self, host: str = "0.0.0.0", port: int = 8765) -> None:
        self.host = host
        self.port = port

        self.queue_module = QueueModule()
        self.db = DatabaseHandler()
        self.tool_executor = ToolExecutor()
        self.embeddings = EmbeddingsModule()

    async def start(self) -> None:
        async with websockets.serve(self._connection_handler, self.host, self.port):
            await asyncio.Future()
    
    async def _connection_handler(self, websocket) -> None:
        parsed_url = urlparse(websocket.path)
        query_params = parse_qs(parsed_url.query)

        session_id = query_params.get("session_id", ["default_session"])[0]
        user_id = query_params.get("user_id", ["anonymous_user"])[0]

        orchestrator = ConversationOrchestrator(
            session_id=session_id, 
            user_id=user_id, 
            queue=self.queue_module, 
            db=self.db, 
            executor=self.tool_executor, 
            embeddings=self.embeddings
        )

        outbound_queue: asyncio.Queue = asyncio.Queue()
        sender_task = asyncio.create_task(self._outbound_sender_loop(websocket, outbound_queue))
        processing_task: asyncio.Task | None = None

        try:
            async for raw_data in websocket:
                try:
                    event = json.loads(raw_data)
                    event_type = event.get("type")
                    payload = event.get("payload", {})
                except json.JSONDecodeError:
                    await outbound_queue.put({"type": "error", "content": "Malformed JSON structure."})
                    continue

                if event_type == "barge":
                    await orchestrator.handle_event("barge", payload)
                    if processing_task and not processing_task.done():
                        processing_task.cancel()

                    while not outbound_queue.empty():
                        try:
                            outbound_queue.get_nowait()
                            outbound_queue.task_done()
                        except (asyncio.QueueEmpty, ValueError):
                            break
                    await outbound_queue.put({"type": "status", "content": "interrupted"})

                elif event_type == "text":
                    if processing_task and not processing_task.done():
                        processing_task.cancel()
                        
                    processing_task = asyncio.create_task(
                        self._process_and_stream_tokens(orchestrator, payload, outbound_queue)
                    )

        except websockets.ConnectionClosed:
            pass
        finally:
            if processing_task and not processing_task.done():
                processing_task.cancel()
            if orchestrator._active_task and not orchestrator._active_task.done():
                orchestrator._active_task.cancel()
                
            await outbound_queue.put(None)
            await sender_task

    async def _outbound_sender_loop(self, websocket, outbound_queue: asyncio.Queue) -> None:
        try:
            while True:
                message = await outbound_queue.get()
                if message is None:
                    break
                await websocket.send(json.dumps(message))
                outbound_queue.task_done()
        except asyncio.CancelledError:
            pass

    async def _process_and_stream_tokens(self, orchestrator: ConversationOrchestrator, payload: dict, outbound_queue: asyncio.Queue) -> None:
        try:
            async for token in orchestrator.handle_event("text", payload):
                await outbound_queue.put({"type": "token", "content": token})
        except asyncio.CancelledError:
            pass
        except Exception:
            await outbound_queue.put({"type": "error", "content": "An internal framework processing error occurred."})


if __name__ == "__main__":
    server = EntryPoint(host="0.0.0.0", port=8765)
    try:
        asyncio.run(server.start())
    except KeyboardInterrupt:
        pass
