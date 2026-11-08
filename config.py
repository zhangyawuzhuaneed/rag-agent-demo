import os
from pathlib import Path

# 优先从项目根目录的 .env 读取（.env 已加入 .gitignore，不会入库）
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent / ".env")
except ImportError:
    pass  # 没装 python-dotenv 时退化为直接读系统环境变量

# ===== 智谱 =====
ZHIPU_API_KEY = os.getenv("ZHIPU_API_KEY")
if not ZHIPU_API_KEY:
    raise RuntimeError(
        "未找到 ZHIPU_API_KEY。\n"
        "请把 .env.example 复制为 .env 并填入你的智谱 API Key：\n"
        "    cp .env.example .env\n"
        "Key 申请地址：https://open.bigmodel.cn/usercenter/apikeys"
    )

EMBEDDING_MODEL = "embedding-3"
EMBEDDING_DIMENSIONS = 1024          # 256/512/1024/2048，默认 2048
LLM_MODEL = "glm-4-plus"            # 也可用 glm-4-flash 免费
LLM_TEMPERATURE = 0.1

# ===== Chroma =====
PERSIST_DIRECTORY = "./chroma_db"
COLLECTION_NAME = "knowledge_base"

# ===== 切块（中文保守值）=====
CHUNK_SIZE = 500
CHUNK_OVERLAP = 60

# ===== 高德（可选，留空则天气工具返回模拟值）=====
GAODE_KEY = ""

# 写入环境变量，兼容 langchain_community 的读取习惯
os.environ["ZHIPUAI_API_KEY"] = ZHIPU_API_KEY
