# syntax=docker/dockerfile:1.7
FROM node:22-bookworm-slim AS builder

WORKDIR /app

COPY package.json package-lock.json ./
RUN --mount=type=cache,target=/root/.npm npm ci

COPY . .

ARG VITE_API_BASE_URL
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
RUN npm run build


FROM node:22-bookworm-slim AS runtime

WORKDIR /app

RUN useradd --create-home --uid 1000 app

COPY --from=builder --chown=app:app /app/dist ./dist
COPY --from=builder --chown=app:app /app/node_modules ./node_modules
COPY --from=builder --chown=app:app /app/package.json ./package.json

ENV NODE_ENV=production \
    PORT=3000 \
    HOST=0.0.0.0

USER app
EXPOSE 3000

CMD ["npm", "run", "start"]
