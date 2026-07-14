import asyncio
from sentence_transformers import SentenceTransformer

class EmbeddingsModule:
    def __init__(self, model_name: str):
        self.model = SentenceTransformer(model_name)

    async def embed_string(self, text: str) -> list[float]:
        embedding = await asyncio.to_thread(self.model.encode, text)
        return embedding
