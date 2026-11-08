from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_community.chat_models import ChatZhipuAI

import config
from vector_store import VectorStoreService

PROMPT = """你是一个严谨的客服助手。请严格依据知识片段回答问题。
如果片段不足以回答，请明确说“知识库中暂未找到相关信息”，不要编造。

知识片段：
{context}

问题：{question}
回答："""


class RAGService:
    def __init__(self, vector_service: VectorStoreService):
        self.vector_service = vector_service
        self.prompt = ChatPromptTemplate.from_template(PROMPT)
        self.llm = ChatZhipuAI(
            model=config.LLM_MODEL,
            api_key=config.ZHIPU_API_KEY,
            temperature=config.LLM_TEMPERATURE,
        )
        self.chain = self._build_chain()

    def _build_chain(self):
        retriever = self.vector_service.get_retriever(k=4)

        def format_docs(docs):
            return "\n\n".join(d.page_content for d in docs)

        return (
            {"context": retriever | format_docs,
             "question": RunnablePassthrough()}
            | self.prompt
            | self.llm
            | StrOutputParser()
        )

    def invoke(self, question: str) -> str:
        return self.chain.invoke(question)
