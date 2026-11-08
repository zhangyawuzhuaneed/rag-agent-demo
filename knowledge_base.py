import hashlib, json
from pathlib import Path

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

import config
from loaders import load_file, LOADERS
from vector_store import VectorStoreService

DATA_DIR = Path("./data")
STATE_FILE = Path("./.ingest_state.json")

splitter = RecursiveCharacterTextSplitter(
    chunk_size=config.CHUNK_SIZE,
    chunk_overlap=config.CHUNK_OVERLAP,
    separators=["\n\n", "\n", "。", "；", "！", "？", "，", " ", ""],
)


def file_hash(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()[:16]


def load_state():
    return json.loads(STATE_FILE.read_text(encoding="utf-8")) if STATE_FILE.exists() else {}


def save_state(s):
    STATE_FILE.write_text(json.dumps(s, ensure_ascii=False, indent=2), encoding="utf-8")


def build(force_rebuild=False):
    vs = VectorStoreService()
    state = load_state() if not force_rebuild else {}
    new_docs, processed, skipped = [], 0, 0

    for p in DATA_DIR.rglob("*"):
        if not p.is_file() or p.suffix.lower() not in LOADERS:
            continue

        h = file_hash(p)
        if not force_rebuild and state.get(p.name) == h:
            print(f"⏭ 未变化: {p.name}")
            skipped += 1
            continue

        # 文件更新时先删旧块，防止新旧内容同时被召回。
        # force_rebuild 时 state 被清空，若只判断 `p.name in state` 会跳过删除，
        # 导致旧块残留、重复追加（曾出现 3 个文件入库后集合里躺着 6 块）。
        if force_rebuild or p.name in state:
            vs.delete_by_source(p.name)

        raw = load_file(p)
        if not raw:
            continue

        full = "\n\n".join(d.page_content for d in raw)
        chunks = splitter.split_text(full)

        for i, ch in enumerate(chunks):
            if not ch.strip():
                continue
            new_docs.append(Document(
                page_content=ch,
                metadata={"source": p.name, "chunk_idx": i, "file_type": p.suffix.lower()},
            ))

        state[p.name] = h
        processed += 1
        print(f"✅ {p.name}: {len(chunks)} 块")

    if new_docs:
        for i in range(0, len(new_docs), 200):
            vs.add_documents(new_docs[i:i + 200])
        save_state(state)
        print(f"\n🎉 新处理 {processed} 个文件，跳过 {skipped} 个，共 {len(new_docs)} 块")
    else:
        print(f"\n没有新内容（跳过 {skipped} 个）")


if __name__ == "__main__":
    build(force_rebuild=False)
