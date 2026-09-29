#!/bin/sh
exec tini -- /src/src/time/.venv/bin/mcp-server-time --local-timezone UTC
