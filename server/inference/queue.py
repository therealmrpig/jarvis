import asyncio
import itertools
from typing import Any, Optional, AsyncIterator


class InferenceRequest:
    def __init__(self, messages: list, session_id: str, request_type: str, token_queue: asyncio.Queue):
        self.messages = messages
        self.session_id = session_id
        self.request_type = request_type
        self.token_queue = token_queue


class QueueModule:
    def __init__(self, engine: Any) -> None:
        self._engine = engine
        self._queue = asyncio.PriorityQueue()
        self._sequence_gen = itertools.count()
        self._active_generation_task: Optional[asyncio.Task] = None
        self._active_request: Optional[InferenceRequest] = None
        self._worker_loop_task = asyncio.create_task(self._worker_loop())

    async def barge_in(self, session_id: str) -> None:
        if self._active_request:
            if self._active_request.session_id == session_id:
                if self._active_request.request_type == "conversation":
                    if self._active_generation_task:
                        self._active_generation_task.cancel()

    async def submit(self, session_id: str, messages: list, request_type: str = "background") -> AsyncIterator[str]:
        token_queue = asyncio.Queue()
        request = InferenceRequest(
            messages,
            session_id,
            request_type,
            token_queue
        )

        if request_type == "conversation":
            order = 0
        else:
            order = 1

        await self._queue.put((order, next(self._sequence_gen), request))

        try:
            while True:
                token = await token_queue.get()
                if token is None:
                    break
                yield token
        except asyncio.CancelledError:
            raise

    async def _worker_loop(self) -> None:
        while True:
            _, _, request = await self._queue.get()

            self._active_request = request
            self._active_generation_task = asyncio.create_task(self._run_inference(request))

            try:
                await self._active_generation_task
            except asyncio.CancelledError:
                pass
            finally:
                self._queue.task_done()
                self._active_request = None
                self._active_generation_task = None

    async def _run_inference(self, request: InferenceRequest) -> None:
        try:
            async for token in self._engine.generate(request.messages):
                await request.token_queue.put(token)

            await request.token_queue.put(None)

        except asyncio.CancelledError:
            await request.token_queue.put(None)
            raise
