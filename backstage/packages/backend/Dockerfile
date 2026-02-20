# This dockerfile builds an image for the backend package.
# It should be executed with the root of the repo as docker context.
#
# Before building this image, be sure to have run the following commands in the repo root:
#
# yarn install --immutable
# yarn tsc
# yarn build:backend

FROM node:22-bookworm-slim

ENV PYTHON=/usr/bin/python3

RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && \
    apt-get install -y --no-install-recommends python3 g++ build-essential curl && \
    rm -rf /var/lib/apt/lists/*

RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && \
    apt-get install -y --no-install-recommends libsqlite3-dev && \
    rm -rf /var/lib/apt/lists/*

# Inject corporate CA certificate
COPY certs/corporate-ca.pem /tmp/corporate-ca.pem
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates \
    && cp /tmp/corporate-ca.pem /usr/local/share/ca-certificates/corporate-ca.crt \
    && update-ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Pre-download Node.js headers so node-gyp doesn't need to reach the internet during yarn install
RUN NODE_VERSION=$(node --version | sed 's/v//') && \
    mkdir -p /tmp/.node-gyp/${NODE_VERSION} && \
    curl -k https://nodejs.org/download/release/v${NODE_VERSION}/node-v${NODE_VERSION}-headers.tar.gz \
    | tar xz -C /tmp/.node-gyp/${NODE_VERSION} --strip-components=1 && \
    echo "9" > /tmp/.node-gyp/${NODE_VERSION}/installVersion && \
    chmod -R 777 /tmp/.node-gyp

USER node

WORKDIR /app

COPY --chown=node:node .yarn ./.yarn
COPY --chown=node:node .yarnrc.yml ./
COPY --chown=node:node backstage.json ./

ENV NODE_ENV=production
ENV NODE_OPTIONS="--no-node-snapshot"
ENV NODE_EXTRA_CA_CERTS=/etc/ssl/certs/ca-certificates.crt
ENV NODE_TLS_REJECT_UNAUTHORIZED=0
ENV npm_config_nodedir=/tmp/.node-gyp/20.18.3

COPY --chown=node:node yarn.lock package.json packages/backend/dist/skeleton.tar.gz ./
RUN tar xzf skeleton.tar.gz && rm skeleton.tar.gz

RUN --mount=type=cache,target=/home/node/.cache/yarn,sharing=locked,uid=1000,gid=1000 \
    yarn workspaces focus --all --production && rm -rf "$(yarn cache clean)"

ENV NODE_TLS_REJECT_UNAUTHORIZED=

COPY --chown=node:node examples ./examples

COPY --chown=node:node packages/backend/dist/bundle.tar.gz app-config*.yaml ./
RUN tar xzf bundle.tar.gz && rm bundle.tar.gz

CMD ["node", "packages/backend", "--config", "app-config.yaml", "--config", "app-config.production.yaml"]