# Acquisition image for VE-METHOD-MCP-003. The running sandbox does not use the network.
ARG BASE_IMAGE
FROM ${BASE_IMAGE}
USER root
RUN apt-get update \
 && apt-get install -y --no-install-recommends git ca-certificates tini \
 && rm -rf /var/lib/apt/lists/*
WORKDIR /src
RUN git init \
 && git remote add origin https://github.com/modelcontextprotocol/servers.git \
 && git fetch --depth 1 origin f46d9578190b476b3501923ea8977d899e8db2cb \
 && git checkout --detach FETCH_HEAD \
 && test "$(git rev-parse HEAD)" = "f46d9578190b476b3501923ea8977d899e8db2cb"
RUN npm ci -w @modelcontextprotocol/server-filesystem --ignore-scripts \
 && npm run build -w @modelcontextprotocol/server-filesystem \
 && chmod -R a+rX /src
COPY fixtures/ve-pilot-3.txt /app/fixture/ve-pilot-3.txt
COPY image/start.sh /app/start.sh
RUN chmod 755 /app/fixture /app/start.sh \
 && chmod 644 /app/fixture/ve-pilot-3.txt
