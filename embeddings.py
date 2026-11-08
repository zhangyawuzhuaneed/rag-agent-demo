from typing import List
from langchain_core.embeddings import Embeddings
from zhipuai import ZhipuAI
import config


class ZhipuEmbeddings(Embeddings):
    """智谱 Embedding 的最小封装，内置 64 条分批。"""

    def __init__(self, api_key: str = None, model: str = None,
                 dimensions: int = None):
        self.client = ZhipuAI(api_key=api_key or config.ZHIPU_API_KEY)
        self.model = model or config.EMBEDDING_MODEL
        self.dimensions = dimensions or config.EMBEDDING_DIMENSIONS
        self.batch_size = 64

    def _embed_batch(self, texts: List[str]) -> List[List[float]]:
        resp = self.client.embeddings.create(
            model=self.model,
            input=texts,
            dimensions=self.dimensions,
        )
        return [item.embedding for item in resp.data]

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        result = []
        for i in range(0, len(texts), self.batch_size):
            result.extend(self._embed_batch(texts[i: i + self.batch_size]))
        return result

    def embed_query(self, text: str) -> List[float]:
        return self._embed_batch([text])[0]
