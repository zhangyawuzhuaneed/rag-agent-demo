from langchain_core.tools import tool
import config
from rag_core import RAGService


def build_tools(rag_service: RAGService):
    @tool
    def rag_summarize(query: str) -> str:
        """当需要查询产品功能、使用说明、故障排查、保养维护、尺码、售后政策等知识时，使用此工具检索知识库。"""
        return rag_service.invoke(query)

    @tool
    def get_weather(city: str) -> str:
        """查询指定城市的实时天气。"""
        if not config.GAODE_KEY:
            return f"{city}：晴，25℃，适合使用扫地机器人。"
        # 实际接入高德时替换这里
        return f"{city}：天气数据未配置"

    @tool
    def get_user_location() -> str:
        """获取用户当前所在城市（演示用，返回模拟值）。"""
        return "杭州"

    return [rag_summarize, get_weather, get_user_location]
