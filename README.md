# Final Project

Foundation template for a monorepo web app with:

- `apps/web`: TanStack Start frontend
- `apps/api`: FastAPI backend
- `packages/contracts`: placeholder contracts for future API, RAG, and AI Agent boundaries

Infrastructure choices are intentionally deferred.

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
packages/
  contracts/  # shared contracts placeholder
docs/
  adr/        # architecture decision records
```

## Current non-decisions

- Database
- Vector store
- Cache/queue
- LLM provider
- Agent framework
- Deployment target
