import streamlit as st
from vector_store import VectorStoreService
from rag_core import RAGService

st.set_page_config(page_title="服装电商 · 智能客服", page_icon="👕")
st.title("👕 服装电商 · 智能客服")


@st.cache_resource
def get_rag():
    return RAGService(VectorStoreService())


if "messages" not in st.session_state:
    st.session_state.messages = []

for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

if prompt := st.chat_input("例如：我 170 斤适合穿什么尺码？"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("检索中..."):
            answer = get_rag().invoke(prompt)
        st.markdown(answer)
    st.session_state.messages.append({"role": "assistant", "content": answer})
