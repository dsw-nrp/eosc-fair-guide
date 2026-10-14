FROM node:22.23.3-bookworm-slim AS node
FROM python:3.12.15-bookworm

COPY --from=node /usr/local/bin/node /usr/local/bin/node
COPY --from=node /usr/local/lib/node_modules /usr/local/lib/node_modules
RUN ln -s ../lib/node_modules/npm/bin/npm-cli.js /usr/local/bin/npm \
    && ln -s ../lib/node_modules/npm/bin/npx-cli.js /usr/local/bin/npx

ENV PLAYWRIGHT_BROWSERS_PATH=/opt/ms-playwright
WORKDIR /opt/fair-guide-tools
COPY package.json package-lock.json requirements-dev.txt ./
RUN python -m pip install --no-cache-dir -r requirements-dev.txt \
    && npm ci \
    && npx playwright install --with-deps chromium \
    && git config --global --add safe.directory /workspaces/eosc-fair-guide

WORKDIR /workspaces/eosc-fair-guide
