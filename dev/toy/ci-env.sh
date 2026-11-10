#!/bin/bash
# Run a command the way a GitHub runner would: no bytecode setting, no git identity, no run-cell GITHUB_* vars.
# usage: ci-env.sh COMMAND...
cfg=$(mktemp); printf '[user]\n\tuseConfigOnly = true\n' > "$cfg"
exec env -u PYTHONDONTWRITEBYTECODE -u GITHUB_SERVER_URL -u GITHUB_REPOSITORY -u GITHUB_RUN_ID GIT_CONFIG_GLOBAL="$cfg" GIT_CONFIG_NOSYSTEM=1 "$@"
