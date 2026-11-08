import streamlit as st
from langgraph.prebuilt import create_react_agent
from langchain_community.chat_models import ChatZhipuAI

import config
from vector_store import VectorStoreService
from rag_core import RAGService
from tools import build_tools

st.set_page_config(page_title="智扫通 · 智能客服", page_icon="🤖")
st.title("🤖 智扫通 · 智能客服")


@st.cache_resource
def get_agent():
    vs = VectorStoreService()
    rag = RAGService(vs)
    tools = build_tools(rag)

    llm = ChatZhipuAI(
        model=config.LLM_MODEL,
        api_key=config.ZHIPU_API_KEY,
        temperature=config.LLM_TEMPERATURE,
    )

    agent = create_react_agent(
        model=llm,
        tools=tools,
        prompt=(
            "你是智扫通扫地机器人的智能客服助手。"
            "需要产品知识时调用 rag_summarize，"
            "需要天气时调用 get_weather，"
            "不确定用户位置时先调用 get_user_location。"
        ),
    )
    return agent


if "messages" not in st.session_state:
    st.session_state.messages = []

for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

if prompt := st.chat_input("例如：我家在杭州，今天适合用扫地机器人吗？"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Agent 规划中..."):
            result = get_agent().invoke(
                {"messages": [{"role": "user", "content": prompt}]}
            )
            answer = result["messages"][-1].content
        st.markdown(answer)
    st.session_state.messages.append({"role": "assistant", "content": answer})
