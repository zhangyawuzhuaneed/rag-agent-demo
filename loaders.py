from pathlib import Path
from langchain_core.documents import Document

import pymupdf
from docx import Document as DocxDocument


def load_txt(path: Path):
    return [Document(page_content=path.read_text(encoding="utf-8", errors="ignore"),
                     metadata={"source": path.name})]


def load_pdf(path: Path):
    docs = []
    with pymupdf.open(str(path)) as pdf:
        for page_no, page in enumerate(pdf, start=1):
            # flags=0：不把未知字形退回 CID，尽量拿到真实 Unicode
            text = page.get_text("text", flags=0)
            if text.strip():
                docs.append(Document(
                    page_content=text,
                    metadata={"source": path.name, "page": page_no},
                ))
    return docs


def load_docx(path: Path):
    doc = DocxDocument(str(path))
    text = "\n".join(p.text for p in doc.paragraphs if p.text.strip())
    return [Document(page_content=text, metadata={"source": path.name})]


LOADERS = {
    ".txt": load_txt,
    ".md": load_txt,
    ".pdf": load_pdf,
    ".docx": load_docx,
}


def load_file(path: Path):
    loader = LOADERS.get(path.suffix.lower())
    if not loader:
        print(f"⏭ 跳过不支持的格式: {path.name}")
        return []
    try:
        return loader(path)
    except Exception as e:
        print(f"❌ 加载失败 {path.name}: {e}")
        return []
