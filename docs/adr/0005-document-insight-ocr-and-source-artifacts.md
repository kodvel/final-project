# ADR 0005: Document Insight OCR and source artifacts

Status: Superseded by ADR 0006 for artifact naming and ready-state rules. Still valid for the Mistral OCR and PDF extraction baseline.

PDF processing uses Mistral OCR with inline base64 document input to extract markdown from uploaded PDF Sources. The extracted markdown is saved to `storage/extracted/{workspace_id}/{source_id}/ocr.md`, then chunked with Chonkie. LiteLLM labels each chunk and aggregates those labels into Source Artifacts.

PDF-derived artifacts now use the unified Source Artifact model: required `source_summary`, required `source_content`, and optional `source_insight`. `source_summary` stores the document overview, page count, extracted markdown path, chunk metadata path, and warnings. `source_content` stores searchable and citation-ready chunks. `source_insight` stores key findings, assumptions, risks, opportunities, and source quotes.

PDF ready-state now requires `source_content` indexing in ChromaDB. `storage/extracted/{workspace_id}/{source_id}/ocr.md` and `storage/extracted/{workspace_id}/{source_id}/chunks.json` remain the durable extracted files used for retry and re-indexing.

Source processing runs synchronously by default for the demo. `RAG_ENABLE_BACKGROUND_PROCESSING=false` keeps this behavior. Redis/Celery remain optional background infrastructure; if background processing is enabled later but unavailable, processing should fall back to synchronous execution with a warning.

Configuration for this pipeline uses `RAG_*` names: `RAG_MISTRAL_API_KEY`, `RAG_OPENAI_API_BASE_URL`, `RAG_OPENAI_API_KEY`, `RAG_OPENAI_MODEL`, `RAG_MAX_FILE_SIZE_MB`, and `RAG_ENABLE_BACKGROUND_PROCESSING`.
