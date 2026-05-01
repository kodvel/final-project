# ADR 0001: Foundation template

## Status

Accepted

## Context

This assignment needs a shared foundation for three developers. The product idea is not final, but the repository must be ready for a web app, backend API, future RAG work, and future AI Agent work.

## Decision

- Use a monorepo with `pnpm` workspaces and Moonrepo.
- Use TanStack Start for the frontend in `apps/web`.
- Use FastAPI for the backend in `apps/api`.
- Use `packages/contracts` as a placeholder for shared API, RAG, and agent contracts.
- Use Node.js 22 and Python 3.14.
- Use a Dev Container for consistent developer setup.
- Defer infrastructure decisions such as database, vector store, cache, and queue.

## Consequences

- Developers get a runnable baseline before product decisions are final.
- Python is the primary place for future RAG and AI Agent implementation.
- Type sharing between frontend and backend will need OpenAPI/codegen or explicit contract files later.
