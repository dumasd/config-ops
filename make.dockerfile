ARG PY_VER=3.10.17-slim-bookworm


FROM docker.io/node:20.19-bookworm-slim AS configops-node

ARG BASE_PATH="/"
ARG NPM_BUILD_ENV="production"
ARG NPM_NODE_OPTIONS="--max-old-space-size=4096"

RUN apt-get update -qq \
    && apt-get install -yqq --no-install-recommends \
    build-essential \
    python3

ENV BUILD_CMD="build:${NPM_BUILD_ENV}" \
    PUPPETEER_SKIP_CHROMIUM_DOWNLOAD=true \
    NODE_OPTIONS=${NPM_NODE_OPTIONS} \
    VITE_BASE_PATH=${BASE_PATH} \
    VITE_API_BASE_PATH=${BASE_PATH}

# NPM ci first, as to NOT invalidate previous steps except for when package.json changes
WORKDIR /app/configops-frontend

COPY ./configops-frontend/ ./

# This seems to be the most expensive step
RUN echo "VITE_BASE_PATH=${VITE_BASE_PATH}" >> .env.${NPM_BUILD_ENV} && \
    echo "VITE_API_BASE_PATH=${VITE_API_BASE_PATH}" >> .env.${NPM_BUILD_ENV} && \
    npm i -g pnpm && \
    pnpm install && \
    pnpm run ${BUILD_CMD}

######################################################################
# Final lean image...
######################################################################
FROM docker.io/python:${PY_VER} AS lean

ARG BASE_PATH="/"
ARG NPM_BUILD_ENV="production"

WORKDIR /app
ENV LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    FLASK_APP="configops.app:create_app()" \
    CONFIGOPS_HOME="/app/configops" \
    CONFIGOPS_PORT=5000 \
    FLASK_APPLICATION_ROOT=${BASE_PATH}

RUN mkdir -p configops/static configops-frontend \
    && useradd --user-group -d ${CONFIGOPS_HOME} -m --no-log-init --shell /bin/bash configops \
    && apt-get update -qq && apt-get install -yqq --no-install-recommends \
    build-essential \
    curl \
    default-libmysqlclient-dev \
    libecpg-dev \
    libldap2-dev \
    libpq-dev \
    libsasl2-dev \
    libsasl2-modules-gssapi-mit \
    && chown -R configops:configops ./* \
    && rm -rf /var/lib/apt/lists/*

COPY --chown=configops:configops configops-frontend/package.json configops-frontend/
COPY --chown=configops:configops requirements.txt .
COPY --chown=configops:configops migrations/ migrations/
RUN pip install --upgrade setuptools pip && \
    pip install -r requirements.txt

COPY --chown=configops:configops --from=configops-node /app/configops-frontend/dist-${NPM_BUILD_ENV}/ configops/static${BASE_PATH}
COPY --chown=configops:configops configops configops

COPY --chmod=755 ./docker/run-server.sh /usr/bin/
USER configops

EXPOSE ${CONFIGOPS_PORT}

CMD ["/usr/bin/run-server.sh"]
