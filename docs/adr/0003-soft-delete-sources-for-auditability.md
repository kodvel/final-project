# ADR 0003: Soft-delete sources for auditability

Deleting a Source hides it from Source Data lists and future analysis, but keeps enough Source, Source Artifact, and citation history to explain past assistant answers and Decision Brief Drafts. We rejected unconditional hard delete because it would break source-grounded audit trails; original files may be removed only when no past citations or Decision Brief Drafts depend on them.
