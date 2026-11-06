#!/bin/bash
# Check the package against the Agensi rules and build dist/agent-workflow-template.zip.
# usage: dev/package.sh [--root DIR] [--out FILE]
exec python3 "$(dirname "$0")/package.py" "$@"
