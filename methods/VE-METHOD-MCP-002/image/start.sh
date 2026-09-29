#!/bin/sh
# Image-owned launcher. The sandbox process wrapper only passes PATH and LANG.
# These exports are not host environment inheritance.
export PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
exec /usr/bin/tini -s -- node /app/cli.js --headless --browser chromium --no-sandbox --isolated --allow-unrestricted-file-access --no-webmcp
