"""pytest 全局夹具。

关键点：config.py 在 import 时就会检查 ZHIPU_API_KEY，缺失直接抛 RuntimeError。
CI 里没有真实凭证，所以非集成模式下注入一个 dummy 值，让纯单元测试能够 import 项目模块。
集成模式（RUN_INTEGRATION=1）不注入，由 .env / 系统环境变量提供真实 Key。
"""
import json
import os
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

if os.getenv("RUN_INTEGRATION") != "1":
    os.environ.setdefault("ZHIPU_API_KEY", "pytest-dummy-key-not-for-api-calls")


@pytest.fixture(scope="session")
def repo_root() -> Path:
    return REPO_ROOT


@pytest.fixture(scope="session")
def data_dir(repo_root) -> Path:
    return repo_root / "data"


@pytest.fixture(scope="session")
def eval_cases() -> dict:
    path = REPO_ROOT / "tests" / "eval_cases.json"
    return json.loads(path.read_text(encoding="utf-8"))
