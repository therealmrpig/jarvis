import ollama
from typing import AsyncIterator


class LanguageModelModule:
    def __init__(self, model: str) -> None:
        self._client = ollama.AsyncClient()
        self._model = model

    async def generate(self, messages: list) -> AsyncIterator[str]:
        response = await self._client.chat(
            model=self._model,
            messages=messages,
            stream=True
        )

        async for chunk in response:
            token = chunk["message"]["content"]

            if token:
                yield token
