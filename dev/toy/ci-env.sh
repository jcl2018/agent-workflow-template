#!/bin/bash
# Run a command the way a GitHub runner would: no bytecode setting, no git identity. usage: ci-env.sh COMMAND...
cfg=$(mktemp); printf '[user]\n\tuseConfigOnly = true\n' > "$cfg"
exec env -u PYTHONDONTWRITEBYTECODE GIT_CONFIG_GLOBAL="$cfg" GIT_CONFIG_NOSYSTEM=1 "$@"
