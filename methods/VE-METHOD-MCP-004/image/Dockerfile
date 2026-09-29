# Acquisition image for VE-METHOD-MCP-004. The running sandbox does not use the network.
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
# Distro tzdata is intentionally absent. ZoneInfo then uses the locked Python tzdata.
# uv's default interpreter lives under /root, which uid 65532 cannot traverse.
ENV UV_PYTHON_INSTALL_DIR=/opt/uv-python
RUN pip install --no-cache-dir uv \
 && mkdir -p /opt/uv-python \
 && cd /src/src/time \
 && uv sync --frozen --no-dev \
 && rm -rf /usr/share/zoneinfo \
 && chmod -R a+rX /src /opt/uv-python
COPY image/start.sh /app/start.sh
RUN chmod 755 /app/start.sh
