# Acquisition image for VE-METHOD-MCP-002. Runtime does not use this file to pull.
ARG BASE_IMAGE
FROM ${BASE_IMAGE}
USER root
WORKDIR /app
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
COPY package.json package-lock.json cli.js ./
RUN npm ci --omit=dev --ignore-scripts \
 && npx playwright-core install-deps chromium \
 && npx playwright-core install chromium \
 && apt-get update \
 && apt-get install -y --no-install-recommends tini \
 && rm -rf /var/lib/apt/lists/* \
 && chmod -R a+rX /app /ms-playwright
COPY ve-pilot-2.html /app/fixture/ve-pilot-2.html
COPY start.sh /app/start.sh
RUN chmod 755 /app/start.sh
