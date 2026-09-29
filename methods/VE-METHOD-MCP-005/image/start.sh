#!/bin/sh
# The graph file is on the sandbox's existing isolated tmpfs. It is not a host path.
export MEMORY_FILE_PATH=/tmp/ve-pilot-5.jsonl
exec tini -- node /src/src/memory/dist/index.js
