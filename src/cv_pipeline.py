from __future__ import annotations

import argparse
import hashlib
import os
import re
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
MARKDOWN_DIR = PROJECT_ROOT / "data" / "markdown"
CHROMA_DIR = PROJECT_ROOT / "data" / "chroma"
COLLECTION_NAME = "candidate_cvs"
SILICONFLOW_EMBEDDING_URL = "https://api.siliconflow.com/v1/embeddings"
EMBEDDING_MODEL = "Qwen/Qwen3-Embedding-4B"
SECTION_ALIASES = {
    "hoc van": "# Học vấn",
    "giao duc": "# Học vấn",
    "education": "# Học vấn",
    "kinh nghiem": "# Kinh nghiệm",
    "kinh nghiem lam viec": "# Kinh nghiệm",
    "work experience": "# Kinh nghiệm",
    "experience": "# Kinh nghiệm",
    "ky nang": "# Kỹ năng",
    "technical skills": "# Kỹ năng",
    "skills": "# Kỹ năng",
    "du an": "# Dự án",
    "projects": "# Dự án",
    "chung chi": "# Chứng chỉ",
    "certifications": "# Chứng chỉ",
    "ngoai ngu": "# Ngoại ngữ",
    "languages": "# Ngoại ngữ",
    "hoat dong": "# Hoạt động",
    "activities": "# Hoạt động",
    "about me": "# Giới thiệu",
    "summary": "# Giới thiệu",
    "hobby": "# Sở thích",
    "hobbies": "# Sở thích",
    "so thich": "# Sở thích",
}
DATE_RANGE_RE = re.compile(
    r"^(\d{1,2}/\d{3,4}\s*-\s*\d{1,2}/\d{4}|"
    r"\d{1,2}/\d{3,4}\s+\d{1,2}/\d{4}|"
    r"\d{4}\s*-\s*(?:NOW|Now|now|\d{4}))\s*(.*)$"
)


def chunk_markdown(markdown: str, max_chars: int = 1200, overlap_chars: int = 150) -> list[str]:
    paragraphs = [part.strip() for part in markdown.split("\n\n") if part.strip()]
    chunks: list[str] = []

    for paragraph in paragraphs:
        if not chunks or len(chunks[-1]) + len(paragraph) + 2 > max_chars:
            prefix = chunks[-1][-overlap_chars:] if chunks and overlap_chars else ""
            chunks.append((prefix + "\n\n" + paragraph).strip() if prefix else paragraph)
        else:
            chunks[-1] = f"{chunks[-1]}\n\n{paragraph}"

    return chunks


def _plain_heading_key(line: str) -> str:
    line = re.sub(r"^[#>*\-\s]+|[*_`:\-\s]+$", "", line.strip())
    line = unicodedata.normalize("NFD", line)
    line = "".join(char for char in line if unicodedata.category(char) != "Mn")
    line = re.sub(r"[^a-zA-Z0-9 ]+", " ", line).lower()
    return re.sub(r"\s+", " ", line).strip()


def _strip_icons(line: str) -> str:
    return "".join(
        char
        for char in line
        if unicodedata.category(char) not in {"So", "Co"}
    )


def clean_cv_markdown(markdown: str) -> str:
    markdown = re.sub(r"!\[[^\]]*]\([^)]*\)", "", markdown)
    markdown = re.sub(r"<img\b[^>]*>", "", markdown, flags=re.IGNORECASE)

    lines = []
    previous_blank = False
    for raw_line in markdown.splitlines():
        line = _strip_icons(raw_line).strip()
        heading = SECTION_ALIASES.get(_plain_heading_key(line))
        if heading:
            line = heading
        if not line:
            if not previous_blank:
                lines.append("")
            previous_blank = True
            continue
        lines.append(line)
        previous_blank = False

    return "\n".join(lines).strip()


def _emit_line(lines: list[str], line: str) -> None:
    if lines and lines[-1] != "":
        lines.append("")
    lines.append(line)


def _append_bullet(lines: list[str], text: str) -> None:
    text = text.strip()
    if not text:
        return
    if lines and lines[-1].startswith("### "):
        lines[-1] = f"{lines[-1]} {text}"
    else:
        _emit_line(lines, f"### {text}")


def _append_text(lines: list[str], text: str) -> None:
    text = text.strip()
    if not text:
        return
    if lines and lines[-1].startswith("### "):
        lines[-1] = f"{lines[-1]} {text}"
    elif lines and lines[-1].startswith("## "):
        _emit_line(lines, f"### {text}")
    else:
        _emit_line(lines, text)


def format_cv_blocks(blocks: list[tuple[int, float, float, str]]) -> str:
    lines: list[str] = []

    for _page, _x, _y, raw_text in sorted(blocks, key=lambda block: (block[0], block[2], block[1])):
        text = clean_cv_markdown(raw_text.replace("\n", " ")).strip()
        if not text:
            continue

        heading = SECTION_ALIASES.get(_plain_heading_key(text))
        if heading:
            _emit_line(lines, heading)
            continue

        date_match = DATE_RANGE_RE.match(text)
        if date_match:
            date, rest = date_match.groups()
            date = re.sub(r"\s+", " ", date.replace(" - ", " - ")).strip()
            rest = rest.strip(" |")
            suffix = f" - {rest}" if rest else ""
            _emit_line(lines, f"## {date}{suffix}")
            continue

        parts = [part.strip() for part in re.split(r"\s*•\s*", text) if part.strip()]
        if text.lstrip().startswith("•"):
            for part in parts:
                _emit_line(lines, f"### {part}")
        elif len(parts) > 1:
            _append_text(lines, parts[0])
            for part in parts[1:]:
                _emit_line(lines, f"### {part}")
        else:
            _append_text(lines, text)

    return "\n".join(lines).strip()


def extract_cv_blocks(pdf_file: Path) -> list[tuple[int, float, float, str]]:
    import pymupdf

    blocks = []
    with pymupdf.open(pdf_file) as doc:
        for page_index, page in enumerate(doc):
            for block in page.get_text("dict")["blocks"]:
                if block.get("type") != 0:
                    continue
                lines = []
                for line in block["lines"]:
                    line_text = "".join(span["text"] for span in line["spans"]).strip()
                    if line_text:
                        lines.append(line_text)
                if lines:
                    x0, y0, _x1, _y1 = block["bbox"]
                    blocks.append((page_index, x0, y0, "\n".join(lines)))
    return blocks


def record_id(source_file: Path, chunk_index: int) -> str:
    digest = hashlib.sha1(str(source_file).encode("utf-8")).hexdigest()[:16]
    return f"{digest}-{chunk_index}"


def build_metadata(
    source_file: Path,
    markdown_file: Path,
    chunk_index: int,
    ingested_at: str | None = None,
) -> dict[str, str | int]:
    return {
        "source_file": str(source_file),
        "markdown_file": str(markdown_file),
        "chunk_index": chunk_index,
        "candidate_name": source_file.stem,
        "ingested_at": ingested_at or datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


def require_siliconflow_api_key(env: dict[str, str] | os._Environ[str] = os.environ) -> str:
    api_key = env.get("SILICONFLOW_API_KEY")
    if not api_key or api_key == "your_siliconflow_api_key_here":
        raise RuntimeError("SILICONFLOW_API_KEY is required for embeddings")
    return api_key


def build_siliconflow_embedding_payload(texts: list[str]) -> dict[str, str | list[str]]:
    return {
        "model": os.getenv("SILICONFLOW_EMBEDDING_MODEL") or EMBEDDING_MODEL,
        "input": texts,
        "encoding_format": "float",
    }


def parse_siliconflow_embeddings(data: dict) -> list[list[float]]:
    return [item["embedding"] for item in data["data"]]


def pdf_to_markdown(pdf_file: Path, markdown_dir: Path = MARKDOWN_DIR) -> Path:
    markdown = format_cv_blocks(extract_cv_blocks(pdf_file))
    if not markdown:
        raise ValueError(f"No text extracted from {pdf_file}")

    markdown_dir.mkdir(parents=True, exist_ok=True)
    markdown_file = markdown_dir / f"{pdf_file.stem}.md"
    markdown_file.write_text(markdown, encoding="utf-8")
    return markdown_file


def embed_texts(texts: list[str]) -> list[list[float]]:
    import requests

    response = requests.post(
        SILICONFLOW_EMBEDDING_URL,
        json=build_siliconflow_embedding_payload(texts),
        headers={
            "Authorization": f"Bearer {require_siliconflow_api_key()}",
            "Content-Type": "application/json",
        },
        timeout=60,
    )
    response.raise_for_status()
    return parse_siliconflow_embeddings(response.json())


def upsert_cv_chunks(
    pdf_file: Path,
    markdown_file: Path,
    chunks: list[str],
    embeddings: list[list[float]],
    chroma_dir: Path = CHROMA_DIR,
) -> int:
    import chromadb

    chroma_dir.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(chroma_dir))
    collection = client.get_or_create_collection(name=COLLECTION_NAME)
    source = pdf_file.resolve()
    generated = markdown_file.resolve()
    ingested_at = datetime.now(timezone.utc).isoformat(timespec="seconds")

    collection.delete(where={"source_file": str(source)})
    collection.upsert(
        ids=[record_id(source, index) for index in range(len(chunks))],
        documents=chunks,
        embeddings=embeddings,
        metadatas=[
            build_metadata(source, generated, index, ingested_at=ingested_at)
            for index in range(len(chunks))
        ],
    )
    return len(chunks)


def ingest_cv(pdf_path: str) -> int:
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except ModuleNotFoundError:
        pass

    pdf_file = Path(pdf_path)
    if not pdf_file.exists() or pdf_file.suffix.lower() != ".pdf":
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    require_siliconflow_api_key()
    pdf_file = pdf_file.resolve()
    markdown_file = pdf_to_markdown(pdf_file)
    chunks = chunk_markdown(markdown_file.read_text(encoding="utf-8"))
    if not chunks:
        raise ValueError(f"No chunks created from {markdown_file}")

    embeddings = embed_texts(chunks)
    return upsert_cv_chunks(pdf_file, markdown_file, chunks, embeddings)


def main() -> int:
    parser = argparse.ArgumentParser(description="Ingest a candidate CV PDF into local ChromaDB.")
    parser.add_argument("pdf", help="Path to a candidate CV PDF")
    args = parser.parse_args()

    try:
        count = ingest_cv(args.pdf)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(f"Ingested {count} chunks into Chroma collection '{COLLECTION_NAME}'.")
    print(f"Markdown: {MARKDOWN_DIR / (Path(args.pdf).stem + '.md')}")
    print(f"Chroma: {CHROMA_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
