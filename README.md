# Final Project

Foundation template for a monorepo web app with:

- `apps/web`: TanStack Start frontend
- `apps/api`: FastAPI backend

Backend API validation lives in FastAPI/Pydantic/SQLModel. Frontend TypeScript types live in `apps/web/src/types`.

## Requirements

- Node.js 22
- Python 3.14
- pnpm 10
- uv

Recommended: open the repo in the Dev Container.

## Quick start

```bash
corepack enable
pnpm install
cd apps/api && uv sync && cd ../..
pnpm dev
```

Services:

- Web: <http://localhost:3000>
- API health: <http://localhost:8000/health>
- API docs: <http://localhost:8000/docs>
- Scalar API reference: <http://localhost:8000/scalar>

## Common commands

```bash
pnpm dev      # run apps in dev mode
pnpm test     # run smoke tests
pnpm lint     # run type/lint checks
pnpm build    # build runnable targets
pnpm check    # lint + test + build
```

## Repository layout

```txt
apps/
  web/        # TanStack Start
  api/        # FastAPI
docs/
  adr/        # architecture decision records
```

## Current architecture

- Local development database defaults to SQLite at `apps/api/storage/app.db`.
- API documentation is available through FastAPI docs and Scalar.
- Future vector retrieval code belongs in `apps/api/app/knowledge`.
- Future OpenAI Agent SDK orchestration belongs in `apps/api/app/agents`.
- Runtime files under `apps/api/storage` are local-only.
- Deployment target
