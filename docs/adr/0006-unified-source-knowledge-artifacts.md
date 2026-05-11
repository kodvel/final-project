# ADR 0006: Unified source knowledge artifacts

Status: Accepted.

## Context

The earlier Source processing plan treated CSV and PDF outputs differently. CSV processing produced `csv_profile`, `chart_spec`, and `insight_card`. PDF processing produced `source_summary` and `source_insight`, then deferred vector indexing. This made the product model file-type-driven and made Visualization Data depend on per-file artifacts.

The app needs one model for company knowledge. File type should affect extraction, not how the product, Chat, or Visualization Data understands a Source.

## Decision

All ready Sources produce normalized Source Artifacts:

- `source_summary`: required overview of what the Source contains.
- `source_content`: required searchable and citation-ready chunks for indexable Sources.
- `source_insight`: optional findings, risks, opportunities, assumptions, and quotes.

Retire `csv_profile`, `chart_spec`, `insight_card`, and `visualization_spec` as core artifact types.

Source periods use month ranges only:

- `period_start_month`: `YYYY-MM`
- `period_end_month`: `YYYY-MM`

The backend derives display labels such as `Jan 2026` and `Q1 2026`. Users do not enter manual period labels.

Source processing runs synchronously by default for MVP/demo reliability. Redis/Celery remain optional future infrastructure.

SQL remains the source of truth. ChromaDB indexes `source_content.chunks` and can be rebuilt from SQL artifacts and extracted files.

Visualization Data uses a cached `visualization_snapshot` for one Workspace and one month range. It composes ready Source Artifacts and is not a per-Source artifact.

## Consequences

- Chat uses one retrieval facade over SQL-validated ChromaDB results.
- CSV Source content is indexed as summarized factual chunks, not raw rows.
- PDF Source content is indexed as OCR chunks with page references and labels.
- A Source becomes Ready only after required artifacts and required indexing succeed.
- Visualization Data has no team, category, or file type filters in MVP; those labels remain metadata and grouping context.
- Existing code and docs using CSV-specific artifact names must be migrated.
