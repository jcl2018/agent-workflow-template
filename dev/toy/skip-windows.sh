#!/bin/bash
# usage: bash dev/toy/skip-windows.sh "WHY" && <the row's command>
# A row that cannot run on a native Windows PC says so (exit 77: the lane reports SKIPPED, not FAIL). Elsewhere exit 0.
case "$(uname -s)" in MINGW*|MSYS*|CYGWIN*) echo "SKIP: ${1:-cannot run on native Windows}"; exit 77;; esac
