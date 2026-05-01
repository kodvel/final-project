FROM python:3.14-bookworm

ARG NODE_MAJOR=22

RUN apt-get update \
  && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    git \
    gnupg \
  && mkdir -p /etc/apt/keyrings \
  && curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key \
    | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg \
  && echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_${NODE_MAJOR}.x nodistro main" \
    > /etc/apt/sources.list.d/nodesource.list \
  && apt-get update \
  && apt-get install -y --no-install-recommends nodejs \
  && npm install --global corepack@latest \
  && corepack enable \
  && curl -LsSf https://astral.sh/uv/install.sh | sh \
  && ln -s /root/.local/bin/uv /usr/local/bin/uv \
  && apt-get clean \
  && rm -rf /var/lib/apt/lists/*
