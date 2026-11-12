#!/bin/bash
# Run a command the way a GitHub runner would: no bytecode setting, no git identity, no run-cell GITHUB_* vars.
# usage: ci-env.sh COMMAND...
pat=$(mktemp); echo "# a toy: no private names" > "$pat"  # the real list and git hooks never run in a toy
cfg=$(mktemp); printf '[user]\n\tuseConfigOnly = true\n' > "$cfg"
exec env -u PYTHONDONTWRITEBYTECODE -u GITHUB_SERVER_URL -u GITHUB_REPOSITORY -u GITHUB_RUN_ID LOOP_NO_GIT_HOOKS=1 LOOP_PRIVATE_NAMES="${LOOP_PRIVATE_NAMES:-$pat}" GIT_CONFIG_GLOBAL="$cfg" GIT_CONFIG_NOSYSTEM=1 "$@"
