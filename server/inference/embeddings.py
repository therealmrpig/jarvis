import sentence-transformers
from typing import List

class EmbeddingsModule:
    def __init__(self, model_name: str):
        pass

    def embed_string(self, text: str) -> List[float]:
        pass
    
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        pass
