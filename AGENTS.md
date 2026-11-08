# AGENTS.md — 本项目的工作约定

> 任何 AI Agent / 新成员在动手前**先读完本文件**。这是跨会话的长效记忆。
> 详细原理不要在这里找，按文末「文档索引」按需加载对应分册。

## 1. 项目是什么

手写实现的 **RAG + ReAct Agent 智能客服 Demo**，用于学习 RAG 全链路。
两个 Streamlit 入口共用同一套检索内核：

| 入口 | 范式 | 业务域 |
|---|---|---|
| `rag_app.py` | 纯 RAG（固定：检索 → 生成） | 服装电商 |
| `agent_app.py` | LangGraph ReAct Agent（LLM 自主调工具） | 扫地机器人 |

**数据流**：`data/` → 解析 → 中文切块 → 智谱 embedding → Chroma → 检索 top-4 → Prompt → glm-4-plus → 答案。

## 2. 环境与启动（必读）

- Python **3.13**，虚拟环境在 `.venv/`。依赖锁在 `requirements.txt`，测试依赖在 `requirements-dev.txt`。
- **必须在仓库根目录执行所有命令**。`PERSIST_DIRECTORY = "./chroma_db"` 是相对 CWD 的路径，
  在别处启动会新建一个空向量库，表现为「所有问题都答知识库中暂未找到相关信息」。

```bash
python generate_samples.py        # 1. 生成演示文档（可跳过，data/ 已自带）
python knowledge_base.py          # 2. 建库；改过 data/ 必须重跑
./.venv/Scripts/streamlit.exe run rag_app.py     # 3a. 纯 RAG 界面
./.venv/Scripts/streamlit.exe run agent_app.py   # 3b. Agent 界面
pytest -q                         # 4. 跑测试（纯单元，不调 API）
```

**Streamlit 必须用 `streamlit run` 启动。** 用 `python rag_app.py` 会进入 bare mode，
打印 `missing ScriptRunContext` 且**不会启动任何 Web 服务**。
同时开两个 app 时给第二个加 `--server.port 8502`。

## 3. 目录职责

| 路径 | 职责 |
|---|---|
| `config.py` | 全局配置：Key、模型、维度、切块参数、Chroma 路径 |
| `embeddings.py` | `ZhipuEmbeddings`（`Embeddings` 接口 + 64 条分批） |
| `loaders.py` | TXT/MD/PDF/DOCX → `Document` 列表 |
| `knowledge_base.py` | 离线入库：sha256 增量、切块、写 Chroma |
| `vector_store.py` | Chroma 封装：`get_retriever` / `add_documents` / `delete_by_source` |
| `rag_core.py` | LCEL 管道 + 防幻觉 Prompt |
| `tools.py` | 三个 Agent 工具（RAG 被包装成其中一个） |
| `data/` | 知识库原始文档（3 个演示文件） |
| `tests/` | 单元测试 + 评估集 |
| `docs/` | 分层文档（按需读，见 §7） |
| `skills/backend-sdd/` | 规格驱动开发 Skill |
| `.github/workflows/` | CI：pytest + 密钥扫描 |

**不入库**：`.env`、`.venv/`、`chroma_db/`、`.ingest_state.json`、`__pycache__/`、`.pytest_cache/`。

## 4. 关键约定（改代码前必须知道）

1. **Key 只从 `.env` 或系统环境变量读**，`config.py` 缺 Key 直接抛 `RuntimeError`。
   `load_dotenv()` 默认 `override=False` → **系统环境变量优先级高于 `.env`**，改 Key 时留意。
   `config.py` 末尾还会把值回写进 `os.environ["ZHIPUAI_API_KEY"]` 以兼容 `ChatZhipuAI`。
2. **`metadata["source"]` 是纯文件名**，被 `delete_by_source()` 用来做过滤删除。
   改字段名或改成路径会静默破坏「文件更新时先删旧块」的增量逻辑。
3. **改 `EMBEDDING_DIMENSIONS` 必须 `build(force_rebuild=True)` 全量重建**，
   否则新旧向量维度不一致，检索直接失效。
4. **切块参数** `CHUNK_SIZE=500 / CHUNK_OVERLAP=60`，分隔符为中文标点优先，
   不要换回 LangChain 默认的空格分隔（会把中文句子拦腰截断）。
5. **检索距离是 cosine**（`hnsw:space`），建库与查询必须一致。
6. `st.cache_resource` 缓存 `RAGService`，进程内只构建一次，不要挪到每次调用里。
7. Prompt 里的防幻觉句「知识库中暂未找到相关信息」**不得删除**；`LLM_TEMPERATURE=0.1` 同理。

## 5. 硬性禁止（Never）

未经用户逐项明确授权，不得：

- 把 Key / token / 密码写进源码、日志或提交；不得提交 `.env`
- 执行 `DELETE` / `DROP` / `TRUNCATE` 或无 review 的数据迁移
- `git push --force`、rebase 共享分支
- 改动 CI/CD 配置、`.gitignore` 的密钥规则、认证层
- 新增 / 升级运行时依赖（含 `requirements.txt`）；需先写规格并请求批准
- 直接修改 `chroma_db/` 二进制或 `.ingest_state.json`
- 用「跳过测试 / 加 skip / 放宽断言」让 CI 变绿
- 「顺手优化」与当前任务无关的代码

## 6. 开发工作流

涉及**接口、领域逻辑、跨模块改动、数据变更、重构、疑难 Bug** 时，
先读 `skills/backend-sdd/SKILL.md` 并按其执行：规格 → 人工确认（硬卡点）→ 计划 → 实现 → 验证 → 回写。

任务的验收标准必须可自动化验证；改完必须跑 `pytest -q` 并贴真实输出。

## 7. 文档索引（按需加载，不要一次全读）

| 想了解什么 | 读哪个 |
|---|---|
| 整体架构、文件速查、一图看懂 | `docs/项目架构与新人学习指南.md`（主文档） |
| 离线 / 在线 / Agent 三条链路细节 | `docs/链路详解.md` |
| 跑通步骤、验证清单、常见疑问、动手练习 | `docs/上手与练习.md` |
| 已知问题、改进方向、已修复记录 | `docs/已知问题与改进.md` |
| 一份填好的规格示例 | `skills/backend-sdd/examples/spec-rag-citation.md` |

## 8. 已知坑点（效能飞轮：踩一次，写一条，永久免疫）

> 每次任务结束，把新踩的坑回写到这里。Agent 开工前必读本表。

| # | 现象 | 根因 / 处理 |
|---|---|---|
| K01 | 所有问题都答「知识库中暂未找到相关信息」 | 没在仓库根目录启动，`./chroma_db` 指向了别处的空库 |
| K02 | `missing ScriptRunContext` 且没有界面 | 用 `python xxx.py` 启动了 Streamlit，必须 `streamlit run` |
| K03 | 改了 `.env` 里 Key 不生效 | 系统环境变量存在时优先于 `.env`（dotenv `override=False`） |
| K04 | 改了 `data/` 但答案不变 | 入库不是自动的，必须重跑 `python knowledge_base.py` |
| K05 | PDF 相关提问一律答「未找到」，手册只有 33 个字符 | `generate_samples.py` 用 fpdf2 `multi_cell` 后未复位光标（默认 `XPos.RIGHT`），正文从页面右边缘渲染被截断。**已修**：显式 `new_x=LMARGIN, new_y=NEXT`；`test_load_pdf_contains_full_manual` 是回归护栏 |
| K06 | `force_rebuild=True` 后集合里出现双倍块 | 原代码 force 时清空 `state`，`if p.name in state` 恒假 → 旧块不删就追加。**已修**为 `if force_rebuild or p.name in state` |
| K07 | 入库后集合莫名变成 0 块 | 多个进程同时持有同一个 `chroma_db/` 的 PersistentClient（如 8501 常驻的 Streamlit 与入库脚本）会互相覆盖。**重建前先停掉运行中的 app** |
| K08 | `git push` 报 `Failed to connect to github.com:443` | DNS 污染解析到 `192.30.252.x` 旧 IP。本机 Clash 7897 可用，已配 `http.https://github.com.proxy`；代理端口变了要同步改 |
| K09 | clone 后依赖行为与本地不一致 | `requirements.txt` 曾锁 2024 版本、实测是 2026 版本，六个包全漂移。**已按 Python 3.13.16 实测对齐**并拆出 `requirements-dev.txt` |
| K10 | `import rag_core` 有 DeprecationWarning | `langchain-community` 已停止维护，未来需迁到独立集成包；当前不影响运行 |
| K11 | 密钥扫描测试自己报警 | 扫描器源码里写了被扫描的字面量，需拆成字符串拼接规避自指 |
| K12 | 8501 端口被占用起不来 | 已有 `agent_app.py` 常驻；第二个 app 用 `--server.port 8502` |

> 回写纪律：每次任务结束，把「现象 → 根因 → 处理」压成一行加进本表。
> 已修复的也要留着——它解释了**为什么现在的代码长这样**，避免有人改回去。
