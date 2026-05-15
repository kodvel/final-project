# syntax=docker/dockerfile:1.7
FROM node:22-bookworm-slim AS builder

RUN npm install -g pnpm@10.10.0

WORKDIR /repo

COPY pnpm-lock.yaml pnpm-workspace.yaml package.json ./
COPY apps/web/package.json apps/web/

RUN --mount=type=cache,target=/root/.local/share/pnpm/store \
    pnpm install --frozen-lockfile --filter @final-project/web...

COPY apps/web/ apps/web/

ARG VITE_API_BASE_URL
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
RUN pnpm --filter @final-project/web build

RUN --mount=type=cache,target=/root/.local/share/pnpm/store \
    pnpm --filter @final-project/web --prod --legacy deploy /deploy


FROM node:22-bookworm-slim AS runtime

WORKDIR /app

RUN useradd --create-home --uid 1001 app

COPY --from=builder --chown=app:app /deploy/node_modules ./node_modules
COPY --from=builder --chown=app:app /repo/apps/web/dist ./dist
COPY --from=builder --chown=app:app /repo/apps/web/package.json ./package.json

ENV NODE_ENV=production \
    PORT=3000 \
    HOST=0.0.0.0

USER app
EXPOSE 3000

CMD ["npm", "run", "start"]
