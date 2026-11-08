from langchain_chroma import Chroma
import config
from embeddings import ZhipuEmbeddings


class VectorStoreService:
    def __init__(self, embedding=None):
        self.embedding = embedding or ZhipuEmbeddings()
        self.store = Chroma(
            collection_name=config.COLLECTION_NAME,
            embedding_function=self.embedding,
            persist_directory=config.PERSIST_DIRECTORY,
            collection_metadata={"hnsw:space": "cosine"},  # 中文语义检索用余弦更稳
        )

    def get_retriever(self, k: int = 4):
        return self.store.as_retriever(search_kwargs={"k": k})

    def add_documents(self, docs):
        self.store.add_documents(docs)

    def delete_by_source(self, source: str):
        """文件更新时先删旧块，避免新旧内容同时被召回。"""
        self.store.delete(where={"source": source})
