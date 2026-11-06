#!/bin/bash
# Link the skills into your personal Claude Code skills folder, for every repo on this machine.
# usage: dev/install-local.sh
set -e
here=$(cd "$(dirname "$0")/.." && pwd); to=${CLAUDE_SKILLS_DIR:-$HOME/.claude/skills}
mkdir -p "$to"
for skill in "$here"/skills/workflow-*; do
  name=$(basename "$skill")
  if [ -e "$to/$name" ] && [ ! -L "$to/$name" ]; then echo "SKIP $name: $to/$name is not a link"; continue; fi
  ln -sfn "$skill" "$to/$name"; echo "LINKED $name"
done
