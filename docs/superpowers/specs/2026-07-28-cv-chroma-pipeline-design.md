# CV Chroma Pipeline Design

## Goal

Build a local Python pipeline that converts a candidate CV PDF to Markdown,
embeds the Markdown chunks, attaches useful metadata, and writes them to a
local ChromaDB database inside the project.

## Scope

- Input: one PDF file path from the command line.
- Output: Markdown in `data/markdown/` and Chroma data in `data/chroma/`.
- Vector database: local ChromaDB persistent store, no external Chroma server.
- PDF parser: `pymupdf4llm.to_markdown(..., header=False, footer=False)`.
- Embeddings: OpenAI `text-embedding-3-small`, using `OPENAI_API_KEY`.
- No LangChain layer; Chroma and PyMuPDF4LLM are enough.

## Architecture

Add `src/cv_pipeline.py` as a focused CLI/module.

Pipeline:

1. Validate that the input PDF exists.
2. Convert PDF to Markdown with PyMuPDF4LLM.
3. Save Markdown beside project data, under `data/markdown/<pdf-stem>.md`.
4. Chunk Markdown by paragraphs with a fixed character budget and small overlap.
5. Embed chunks with OpenAI.
6. Upsert into a Chroma collection.

## Metadata

Each Chroma record stores:

- `source_file`: original PDF path as a string.
- `markdown_file`: generated Markdown path as a string.
- `chunk_index`: zero-based chunk number.
- `candidate_name`: PDF filename stem.
- `ingested_at`: UTC ISO timestamp.

Record IDs are deterministic from the source path and chunk index so re-running
the same PDF updates the same records.

## Error Handling

- Missing PDF path exits with a clear CLI error.
- Missing `OPENAI_API_KEY` exits before ingestion.
- Empty Markdown exits before embedding.

## Testing

Add one small assert-based test module for chunking, metadata, and deterministic
record IDs. Avoid PDF parsing and API calls in tests.
