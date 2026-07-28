from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[1]))

from src.cv_pipeline import (
    build_metadata,
    build_siliconflow_embedding_payload,
    chunk_markdown,
    clean_cv_markdown,
    format_cv_blocks,
    parse_siliconflow_embeddings,
    record_id,
    require_siliconflow_api_key,
)


def test_chunk_markdown_splits_paragraphs_with_overlap():
    markdown = "A" * 700 + "\n\n" + "B" * 700 + "\n\n" + "C" * 200

    chunks = chunk_markdown(markdown, max_chars=900, overlap_chars=50)

    assert len(chunks) == 3
    assert chunks[0] == "A" * 700
    assert chunks[1].startswith("A" * 50)
    assert "B" * 700 in chunks[1]
    assert chunks[2].startswith("B" * 50)
    assert "C" * 200 in chunks[2]


def test_metadata_and_ids_are_stable():
    source = Path("candidates/nguyen-van-a.pdf")
    markdown = Path("data/markdown/nguyen-van-a.md")

    assert record_id(source, 2) == record_id(source, 2)
    assert record_id(source, 2) != record_id(source, 3)

    metadata = build_metadata(
        source,
        markdown,
        2,
        ingested_at="2026-07-28T00:00:00+00:00",
    )

    assert metadata == {
        "source_file": str(source),
        "markdown_file": str(markdown),
        "chunk_index": 2,
        "candidate_name": "nguyen-van-a",
        "ingested_at": "2026-07-28T00:00:00+00:00",
    }


def test_require_siliconflow_api_key_rejects_missing_or_placeholder():
    for env in [{}, {"SILICONFLOW_API_KEY": "your_siliconflow_api_key_here"}]:
        try:
            require_siliconflow_api_key(env)
        except RuntimeError as exc:
            assert "SILICONFLOW_API_KEY" in str(exc)
        else:
            raise AssertionError("missing key should fail")

    assert require_siliconflow_api_key({"SILICONFLOW_API_KEY": "sk-test"}) == "sk-test"


def test_siliconflow_payload_and_response_parsing():
    payload = build_siliconflow_embedding_payload(["one", "two"])

    assert payload == {
        "model": "Qwen/Qwen3-Embedding-4B",
        "input": ["one", "two"],
        "encoding_format": "float",
    }

    embeddings = parse_siliconflow_embeddings(
        {"data": [{"embedding": [0.1, 0.2]}, {"embedding": [0.3, 0.4]}]}
    )

    assert embeddings == [[0.1, 0.2], [0.3, 0.4]]


def test_clean_cv_markdown_removes_images_icons_and_normalizes_section_headers():
    raw = """
![avatar](avatar.png)
\uf133 03/07/2004 \uf095 0931654704 📧 email@example.com
**EDUCATION**
VinUni

💼 Kinh nghiệm làm việc
AI Intern

<img src="logo.png">
Technical Skills
Python, RAG

HOBBY
Music
"""

    cleaned = clean_cv_markdown(raw)

    assert "![avatar]" not in cleaned
    assert "<img" not in cleaned
    assert "\uf133" not in cleaned
    assert "\uf095" not in cleaned
    assert "📧" not in cleaned
    assert "💼" not in cleaned
    assert "# Học vấn" in cleaned
    assert "# Kinh nghiệm" in cleaned
    assert "# Kỹ năng" in cleaned
    assert "# Sở thích" in cleaned
    assert "Python, RAG" in cleaned


def test_clean_cv_markdown_keeps_meaningful_symbols():
    assert "C++" in clean_cv_markdown("Skills\nC++ / C#")


def test_format_cv_blocks_keeps_experience_items_in_visual_order():
    blocks = [
        (1, 249.2, 492.0, "EXPERIENCE"),
        (1, 43.0, 526.8, "3/2026 - 7/2026\nGlobal AI | AI Engineer Internship"),
        (1, 178.0, 544.8, "• Built an MCP server for AI Agents integrated with Odoo, enabling agents to"),
        (1, 178.0, 559.8, "access business data.\n• Created an Agent workflow for recruitment:"),
        (1, 43.0, 748.6, "3/206 - 7/2026\nBachelor last year project | Building a respiratory consultant chatbot"),
        (1, 178.0, 810.8, "• Deployed the project to a web environment:"),
        (2, 207.2, 3.7, "• Simple authentication with Clerk."),
        (2, 43.0, 106.4, "8/2025 - 11/2025\n1C Vietnam | Software developer internship"),
        (2, 178.0, 138.6, "• Studied 1C:Enterprise development environment\n• Learned professional workflow"),
        (2, 270.6, 378.1, "SKILLS"),
    ]

    markdown = format_cv_blocks(blocks)

    heading = markdown.index("# Kinh nghiệm")
    first = markdown.index("## 3/2026 - 7/2026 - Global AI")
    second = markdown.index("## 3/206 - 7/2026 - Bachelor last year project")
    third = markdown.index("## 8/2025 - 11/2025 - 1C Vietnam")
    skills = markdown.index("# Kỹ năng")

    assert heading < first < second < third < skills
    assert "### Built an MCP server for AI Agents integrated with Odoo, enabling agents to access business data." in markdown
    assert "### Created an Agent workflow for recruitment:" in markdown
    assert "### Simple authentication with Clerk." in markdown


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
