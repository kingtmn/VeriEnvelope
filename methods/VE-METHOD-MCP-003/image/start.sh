#!/bin/sh
exec tini -- node /src/src/filesystem/dist/index.js /app/fixture
