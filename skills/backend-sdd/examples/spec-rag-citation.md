# SPEC: 检索结果溯源（来源文件 + PDF 页码）

> 本文件是 `SKILL.md` §3 模板的**填写示范**，取自本仓库「已知问题」第 3 条。
> 状态：**示例，未实施**。用来展示每条该写到什么颗粒度，特别是 Open Questions 如何阻止 Agent 自行脑补。

## Goal

问答结果中，每个被引用的知识片段都能追溯到具体来源文件；PDF 来源还需给出页码。
让客服回答「滤网多久换一次」时，能够附带「来源：扫地机器人用户手册.pdf 第 2 页」。

## Non-goals

- 不改动 Streamlit 两个界面的布局与交互，只让答案文本带上来源信息
- 不引入 Rerank、不调整 `top-k`、不更换 Embedding 模型或维度
- 不改动 `PROMPT` 的防幻觉约束（「知识库中暂未找到相关信息」必须保留）
- 不做引用可点击跳转、不做前端高亮
- 不改 `data/` 下的原始文档

## Context

- 涉及文件：`loaders.py`、`knowledge_base.py`、`rag_core.py`、`config.py`
- 现状根因：
  - `load_pdf()` 已为每页 `Document` 写入 `metadata["page"]`
  - 但 `knowledge_base.build()` 用 `"\n\n".join(...)` 把多页拼成整篇后重新切块，
    生成的新 `Document` 只带 `{source, chunk_idx, file_type}`，**page 在合并时丢失**
  - `rag_core.format_docs()` 只拼接 `page_content`，metadata 完全没进 prompt
- 必须保留的能力：`VectorStoreService.delete_by_source()` 依赖 `metadata["source"]` 做过滤删除，
  增量入库的「文件更新时先删旧块」逻辑不能被破坏
- 环境前提：必须在**仓库根目录**运行（`PERSIST_DIRECTORY = "./chroma_db"` 是相对路径）；
  现有 `chroma_db/` 是旧 schema 数据，改 metadata 后需全量重建
- 可复用的既有实现：`file_hash()`、`load_state()` / `save_state()`、`build(force_rebuild=...)`

## Constraints

- 技术：改为**逐页切块**，每页独立 `split_text()`，把该页的 `source` / `page` / `file_type`
  / `chunk_idx` 一并写入 chunk metadata
- 兼容：`source` 字段的值与语义保持不变（仍是纯文件名），否则 `delete_by_source` 失效
- 兼容：`CHUNK_SIZE=500` / `CHUNK_OVERLAP=60` / 中文 `separators` 不变
- 兼容：`EMBEDDING_DIMENSIONS` **不得改动**——改了会导致新旧向量维度不一致
- 依赖：**本次申请新增 dev 依赖 `pytest`**（当前 `requirements.txt` 无测试框架）。
  依 `SKILL.md` §4「不得新增第三方依赖」，此项**必须在 S2 由人显式批准**；未批准则不写测试文件，
  改用临时脚本验证并列入未通过项
- 数据：`build(force_rebuild=True)` 会重写 `.ingest_state.json` 与整个 `chroma_db/`；
  `chroma_db/` 已被 `.gitignore` 排除，`data/` 需保持不变
- 安全：不得把文件内容或 Key 写进日志；不改 `.env` 处理逻辑

## Interfaces

```
# loaders.py
load_pdf(path: Path) -> list[Document]
  Document.metadata = {"source": str, "page": int}     # 保持现状，不改签名

# knowledge_base.build()
  每个 chunk 的 metadata schema:
    {"source": str, "page": int|None, "chunk_idx": int, "file_type": str}
    - PDF   → page = 页码（从 1 开始）
    - 其他  → page = None（见 Open Questions）

# rag_core.format_docs(docs) -> str    ← 行为变更点
  输入: list[Document]（来自 retriever，k=4）
  输出: 每个片段格式化为 "[来源: {source}, 第 {page} 页]\n{page_content}"，用 "\n\n" 连接
  错误: docs 为空 → 返回空字符串（沿用现有行为，由 PROMPT 的防幻觉约束兜底）
         metadata 缺 source → 降级只输出 page_content，不抛异常（兼容旧库中残留的 chunk）
```

## State & Data

- 数据变更：`chroma_db/` 集合 `knowledge_base` 内所有 chunk 的 metadata 增加 `page` 字段
- 迁移方式：`python knowledge_base.py` 改为 `build(force_rebuild=True)` 跑一次全量重建；
  不写迁移脚本，不做原地 patch
- 回滚：删除 `chroma_db/` 与 `.ingest_state.json`，`git checkout` 回退代码后重新入库；
  由于两者均为可重建产物，回滚无数据损失
- 状态：`.ingest_state.json` 的 key 仍是纯文件名，格式不变

## Acceptance Criteria

- [ ] `load_pdf()` 返回的每个 `Document` 仍带正确的 `page`（1-based，与 PDF 实际页序一致）
- [ ] 入库后，PDF 来源的每个 chunk 的 `metadata["page"]` 非空且为 int
- [ ] DOCX / TXT 来源的 chunk 不因新增字段而报错（`page` 处理见 Open Questions）
- [ ] `delete_by_source("扫地机器人用户手册.pdf")` 仍能删净该文件所有 chunk，
      连续两次入库不产生重复片段
- [ ] `format_docs()` 输出中，每个片段前都有来源标注；同一次检索的 4 个片段互不串源
- [ ] `format_docs([])` 返回空字符串
- [ ] 传入缺 `source` 的旧格式 chunk 时不抛异常，降级输出纯文本
- [ ] 提问「滤网多久换一次」，答案仍能给出「3 个月」，且附带来源标注
- [ ] 提问知识库外的问题，答案仍是「知识库中暂未找到相关信息」（防幻觉未被破坏）
- [ ] 回归：服装 DOCX、综合知识 TXT 的原有问答结果不变

## Done When

- [ ] 上述验收项全部有对应测试且通过（或已列明「因 pytest 未批准而改用脚本验证」）
- [ ] `python knowledge_base.py` 全量重建成功，输出块数合理
- [ ] `streamlit run rag_app.py` 手测 3 条问题通过（PDF / DOCX / 库外各一条）
- [ ] `git grep --cached` 扫描无 Key 残留
- [ ] `docs/项目架构与新人学习指南.md` 的「已知问题」第 3 条更新为已修复
- [ ] diff 中无越界改动（未动 `agent_app.py` / `tools.py` / `.env*`）

## Open Questions

> 以下三点 Agent **不得自行假设**，须在 S2 由人拍板后回填本文件：

1. **DOCX / TXT 没有页码，展示成什么？**
   - (a) 只显示文件名 `[来源: 服装售后FAQ.docx]`
   - (b) 显示 `[来源: 服装售后FAQ.docx, 第 1 页]`（把整篇当 1 页）
   - (c) 显示章节标题（需解析 docx heading，工作量增加）
   → 影响 `format_docs` 分支逻辑与「page = None」的约定。

2. **来源标注对最终用户可见，还是仅供调试？**
   → 若对用户可见，需确认文案口径与是否要加免责声明；若仅调试，应走日志而非 prompt。

3. **是否批准新增 `pytest` 作为 dev 依赖？**
   → 不批准则验收项改用脚本验证，测试不进仓库。

---

> 注：本规格起草于项目引入 `pytest` 之前，Open Questions 第 3 条现已由 `requirements-dev.txt` 解决。
> 保留它是为了演示「新增依赖属于需要人工批准的越界项」这一判断环节。

## 示范要点（读完可删）

- **Non-goals 写了 5 条**，其中「不改防幻觉约束」「不动 UI」是最容易被 Agent 顺手改掉的地方。
- **Context 写出了根因和依赖耦合**（`source` 被 `delete_by_source` 依赖），
  否则 Agent 很可能为了「统一 schema」把字段名改掉，悄悄破坏增量入库。
- **Acceptance 里既有正向也有回归**，且每条都能被一条测试或一个命令证伪。
- **Constraints 主动暴露了「新增依赖」这一违规项**，把它抬到 S2 让人决定，而不是先斩后奏。
- **Open Questions 故意留白**，演示「带问题停下来」——这正是 S2 硬卡点的意义。
