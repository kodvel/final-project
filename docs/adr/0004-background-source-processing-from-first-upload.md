# ADR 0004: Background source processing from first upload

Status: Superseded by ADR 0006.

Source upload uses Redis/Celery background processing from the first Source Data vertical slice, so large CSV/PDF processing does not block the request lifecycle. If enqueue or processing fails after upload, the Source remains visible with a Failed Processing Status so the user can retry instead of losing the uploaded input.

Superseding decision: Source processing now runs synchronously by default for MVP/demo reliability. Redis/Celery remain optional later infrastructure.
