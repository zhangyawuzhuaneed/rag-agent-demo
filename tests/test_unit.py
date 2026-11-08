"""纯单元测试：不调用任何外部 API，CI 每次 push 都会跑。

设计原则：
- 把「曾经踩过的坑」变成回归断言，例如 PDF 中文截断、防幻觉 Prompt 被删、Key 硬编码。
- 评估集本身也要被测试，防止写出「源文档里根本没有的答案」这种假评估集。
"""
import re
from pathlib import Path

import pytest

import config
import knowledge_base as kb
import rag_core
from loaders import LOADERS, load_file
from tools import build_tools


# ---------- 配置基线 ----------

def test_config_core_values():
    assert config.EMBEDDING_MODEL == "embedding-3"
    assert config.EMBEDDING_DIMENSIONS == 1024
    assert config.LLM_MODEL == "glm-4-plus"
    assert config.LLM_TEMPERATURE == 0.1
    assert (config.CHUNK_SIZE, config.CHUNK_OVERLAP) == (500, 60)
    assert config.COLLECTION_NAME == "knowledge_base"


# ---------- 文档解析 ----------

def test_loaders_support_expected_formats():
    assert set(LOADERS) >= {".txt", ".md", ".pdf", ".docx"}


def test_load_txt_has_source_metadata(data_dir):
    docs = load_file(data_dir / "综合知识.txt")
    assert len(docs) == 1
    assert docs[0].metadata["source"] == "综合知识.txt"
    assert "100 积分抵扣 1 元" in docs[0].page_content


def test_load_docx_contains_return_policy(data_dir):
    text = "\n".join(d.page_content for d in load_file(data_dir / "服装售后FAQ.docx"))
    assert "7 天内无理由退货" in text
    assert "15 天内可换货" in text


def test_load_pdf_contains_full_manual(data_dir):
    """回归护栏：曾因 fpdf2 multi_cell 光标未复位，PDF 只剩 33 个字符，手册正文全部丢失。"""
    text = "\n".join(d.page_content for d in load_file(data_dir / "扫地机器人用户手册.pdf"))
    assert len(text) > 120, f"PDF 正文疑似被截断，仅 {len(text)} 字符"
    for keyword in ("5000Pa", "400ml", "180 分钟", "3 个月", "不可水洗", "80%"):
        assert keyword in text, f"PDF 缺少关键内容：{keyword}"


def test_load_file_skips_unsupported_format(tmp_path):
    p = tmp_path / "x.xlsx"
    p.write_bytes(b"dummy")
    assert load_file(p) == []


# ---------- 增量入库 ----------

def test_file_hash_stable_and_sensitive(tmp_path):
    p = tmp_path / "a.txt"
    p.write_text("hello", encoding="utf-8")
    h1 = kb.file_hash(p)
    assert len(h1) == 16
    assert kb.file_hash(p) == h1
    p.write_text("hello!", encoding="utf-8")
    assert kb.file_hash(p) != h1


def test_splitter_uses_chinese_separators():
    """中文没有空格分词，分隔符必须包含中文标点，否则句子被拦腰截断。"""
    seps = kb.splitter._separators
    for mark in ("。", "；", "！", "？", "，", "\n\n"):
        assert mark in seps
    assert kb.splitter._chunk_size == config.CHUNK_SIZE
    assert kb.splitter._chunk_overlap == config.CHUNK_OVERLAP


# ---------- Prompt 护栏 ----------

def test_prompt_keeps_antihallucination_guardrail():
    assert "知识库中暂未找到相关信息" in rag_core.PROMPT
    assert "不要编造" in rag_core.PROMPT


def test_prompt_placeholders_match_lcel_keys():
    """LCEL 字典的 key 必须与模板占位符同名，否则运行时 KeyError。"""
    assert "{context}" in rag_core.PROMPT
    assert "{question}" in rag_core.PROMPT


# ---------- Agent 工具 ----------

class _FakeRAG:
    """不连 Chroma / LLM 的替身，让工具定义可以在纯单元环境里被测。"""

    def invoke(self, question):
        return f"stub:{question}"


def test_tools_have_names_and_docstrings():
    """工具 docstring 是 LLM 判断「何时调用」的唯一依据，缺了就失效。"""
    tools = build_tools(_FakeRAG())
    assert {t.name for t in tools} == {"rag_summarize", "get_weather", "get_user_location"}
    for t in tools:
        assert t.description and len(t.description) > 5, f"{t.name} 缺少可用的描述"


def test_rag_tool_delegates_to_service():
    tools = {t.name: t for t in build_tools(_FakeRAG())}
    assert tools["rag_summarize"].invoke("滤网") == "stub:滤网"


def test_weather_and_location_are_documented_mocks():
    tools = {t.name: t for t in build_tools(_FakeRAG())}
    assert "晴" in tools["get_weather"].invoke("杭州")
    assert tools["get_user_location"].invoke({}) == "杭州"


# ---------- 评估集自检 ----------

def test_eval_dataset_structure(eval_cases):
    cases = eval_cases["cases"]
    assert len(cases) == 20, "评估集应为 20 条"
    ids = [c["id"] for c in cases]
    assert len(set(ids)) == len(ids), "评估集 id 必须唯一"
    for c in cases:
        assert c.get("question"), f"{c['id']} 缺少 question"
        if c.get("should_refuse"):
            assert "expected_keywords" not in c, f"{c['id']} 拒答用例不应有期望关键词"
        else:
            assert c.get("expected_keywords"), f"{c['id']} 缺少 expected_keywords"
            assert c.get("source"), f"{c['id']} 缺少 source"
    assert eval_cases["refusal_phrase"] in rag_core.PROMPT


def test_eval_dataset_integrity(eval_cases, data_dir):
    """每条期望答案都必须能在对应源文档里核对——防止编造评估集。"""
    texts = {}
    for c in eval_cases["cases"]:
        src = c.get("source")
        if not src:
            continue
        assert (data_dir / src).exists(), f"{c['id']} 引用了不存在的源文件 {src}"
        if src not in texts:
            texts[src] = "\n".join(d.page_content for d in load_file(data_dir / src))
        hits = [kw for kw in c["expected_keywords"] if kw in texts[src]]
        assert hits, f"{c['id']} 的期望关键词在源文档中一个都找不到：{c['expected_keywords']}"


# ---------- 密钥扫描（本地版，与 CI 的 gitleaks 呼应）----------

def test_no_hardcoded_secret_in_tracked_sources(repo_root):
    skip_dirs = {".venv", "chroma_db", ".git", "__pycache__", ".pytest_cache", "node_modules"}
    # 第一个模式拆开拼接，避免"扫描器自己命中自己"：文件里不能出现完整的泄漏 key 字面量。
    leaked_prefix = "fc35" + "fac6"
    patterns = [
        re.compile(leaked_prefix),
        re.compile(r"""os\.getenv\(\s*["']ZHIPU_API_KEY["']\s*,\s*["'][^"']{20,}"""),
        re.compile(r"""ZHIPU_API_KEY\s*=\s*["'][A-Za-z0-9]{20,}\.[A-Za-z0-9]{10,}"""),
    ]
    offenders = []
    for path in repo_root.rglob("*"):
        if not path.is_file() or any(part in skip_dirs for part in path.parts):
            continue
        if path.suffix.lower() not in {".py", ".md", ".json", ".txt", ".yml", ".yaml", ".ini", ".example"}:
            continue
        if path.name == ".env":
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pat in patterns:
            if pat.search(text):
                offenders.append(f"{path.relative_to(repo_root)} 命中 {pat.pattern}")
    assert not offenders, "疑似密钥硬编码：\n" + "\n".join(offenders)
