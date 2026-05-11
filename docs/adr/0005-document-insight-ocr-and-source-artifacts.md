# ADR 0005: Document Insight OCR and source artifacts

PDF processing uses Mistral OCR with inline base64 document input to extract markdown from uploaded PDF Sources. The extracted markdown is saved to `storage/extracted/{workspace_id}/{source_id}/ocr.md`, then chunked with Chonkie. LiteLLM labels each chunk and aggregates those labels into Source Artifacts.

PDF-derived artifacts use generic Source Artifact names: `source_summary` and `source_insight`. `source_summary` stores the document summary, page count, model names, extracted markdown path, chunk metadata path, and warnings. `source_insight` stores key findings, assumptions, risks, opportunities, and source quotes. The UI calls this view **Document Insight**. It does not use `pdf_summary`, `pdf_insight_board`, or a `document_summary` field inside the insight artifact.

Task 3 writes chunk metadata to `storage/extracted/{workspace_id}/{source_id}/chunks.json` but does not index ChromaDB. Task 4 reads `ocr.md` and `chunks.json` to embed chunks and store retrieval metadata. This keeps OCR, chunk labeling, and artifact generation separate from vector indexing.

Source processing runs synchronously by default for the demo. `RAG_ENABLE_BACKGROUND_PROCESSING=false` keeps this behavior. Redis/Celery remain optional background infrastructure; if background processing is enabled later but unavailable, processing should fall back to synchronous execution with a warning.

Configuration for this pipeline uses `RAG_*` names: `RAG_MISTRAL_API_KEY`, `RAG_OPENAI_API_BASE_URL`, `RAG_OPENAI_API_KEY`, `RAG_OPENAI_MODEL`, `RAG_MAX_FILE_SIZE_MB`, and `RAG_ENABLE_BACKGROUND_PROCESSING`.
