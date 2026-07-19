from typing import Any, AsyncIterator
import re
import json
import asyncio

from server.inference.queue import QueueModule
from server_memory.db_handler import DatabaseHandler
from server.tools.executor import ToolExecutor
from server.inference.embeddings import EmbeddingsModule

class ConversationOrchestrator:
    def __init__(self, session_id: str, user_id: str, queue: QueueModule, db: DatabaseHandler, executor: ToolExecutor, embeddings: EmbeddingsModule) -> None:
        self._session_id = session_id
        self._user_id = user_id
        self._queue = queue
        self._db = db
        self._executor = executor
        self._embeddings = embeddings
        self._history: list[dict[str, str]] = []
        self._active_task: asyncio.Task | None = None

    async def handle_event(self, event_type: str, payload: dict[str, Any]) -> AsyncIterator[str]:
        if event_type == "barge":
            await self._queue.barg_in(self._session_id)
            if self._active_task and not self._active_task.done():
                self._active_task.cancel()
            return

        if event_type == "text":
            user_input = payload.get("text", "")
            if not user_input:
                return
            self._append_to_history("user", user_input)
            loop = asyncio.get_running_loop()
            q = asyncio.Queue()
            self._active_task = loop.create_task(self._run_inference_process(user_input, q))
            try:
                while (token := await q.get()) is not None:
                    yield token
            except asyncio.CancelledError:
                if self._active_task and not self._active_task.done():
                    self._active_task.cancel()
                raise

    async def _run_inference_process(self, user_input: str, q: asyncio.Queue) -> None:
        augmented_messages = list(self._history)
        try:
            query_vec = await self._embeddings.embed_string(user_input)
            memories = self._db.search(self._user_id, query_vec, k=5)
            if memories:
                context = "\n".join(["- " + m['text'] for m in memories])
                augmented_messages.append({"role": "system", "content": f"Context:\n{context}"})
        except Exception:
            pass

        try:
            async for token in self._run_inference_loop(augmented_messages):
                await q.put(token)
        finally:
            await q.put(None)

    async def _run_inference_loop(self, messages: list[dict[str, str]]) -> AsyncIterator[str]:
        token_buffer = ""
        async for token in self._queue.submit(self._session_id, messages, "conversation"):
            token_buffer += token
            yield token

        if token_buffer.strip():
            self._append_to_history("assistant", token_buffer)

        tool_match = re.search(r"<tool>(.*?)</tool>", token_buffer, re.DOTALL)
        if tool_match:
            try:
                tool_call = json.loads(tool_match.group(1))
                result = await self._executor.execute(tool_call)
                self._append_to_history("tool", str(result))
                async for next_token in self._run_inference_loop(list(self._history)):
                    yield next_token
            except Exception as e:
                err = f"Error executing tool: {str(e)}"
                self._append_to_history("system", err)
                yield f"\n[Error: {err}]"

    def _append_to_history(self, role: str, content: str) -> None:
        if content.strip():
            self._history.append({"role": role, "content": content})
