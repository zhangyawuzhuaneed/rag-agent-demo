"""端到端问答评估（质量基线，非确定性单元测试）。

默认跳过。需要真实 Key + 已建好的向量库时：

    RUN_INTEGRATION=1 pytest -q tests/test_eval_integration.py

注意：向量检索总会返回 top-k 片段，"拒答"依赖的是 Prompt 约束而非空检索；
LLM 输出有随机性，失败时应人工判断是「效果退化」还是「措辞变化」，不要盲目放宽断言。
"""
import os

import pytest

RUN = os.getenv("RUN_INTEGRATION") == "1"

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(not RUN, reason="需 RUN_INTEGRATION=1 且配置真实 ZHIPU_API_KEY"),
]


@pytest.fixture(scope="module")
def rag():
    from rag_core import RAGService
    from vector_store import VectorStoreService

    return RAGService(VectorStoreService())


def _cases():
    import json
    from pathlib import Path

    p = Path(__file__).parent / "eval_cases.json"
    return json.loads(p.read_text(encoding="utf-8"))


_DATA = _cases()


@pytest.mark.parametrize("case", _DATA["cases"], ids=lambda c: c["id"])
def test_answer_matches_expectation(rag, case):
    answer = rag.invoke(case["question"])
    assert answer and isinstance(answer, str)

    if case.get("should_refuse"):
        assert _DATA["refusal_phrase"] in answer, (
            f"{case['id']} 应拒答，实际回答：{answer[:200]}"
        )
    else:
        hits = [kw for kw in case["expected_keywords"] if kw in answer]
        assert hits, (
            f"{case['id']} 未命中任何期望关键词 {case['expected_keywords']}，"
            f"实际回答：{answer[:200]}"
        )
