#!/bin/bash
# windows: ok
# reads: skills/workflow-health/scripts/enforce.py skills/workflow-health/scripts/defects.py skills/workflow-setup/scripts/setup.py
# reads: skills/workflow-setup/scripts/agents.py skills/workflow-setup/scripts/settings.py skills/workflow-docs/scripts/entry.py
# reads: dev/toy/test-migration.sh docs/wiki/Setup.md
# The v1 part of test-migration.sh (format gaps, hooks once, owner steps, toolchains) as its own row, so it runs on native Windows:
# the other parts of test-migration.sh already fail there on main (10 checks), so the script as a whole is not marked.
# Value: protects=a feature the template carries is never silently dropped on a new machine: migration-check names it or prints the owner step;
# fails_when=a missing format file, a doubled hook or a missing toolchain goes unnamed, or an owner step fails the check; why_new=adoption on a new PC hit each by hand; seam=none; no_claim=the other parts of test-migration.sh
here=$(cd "$(dirname "$0")" && pwd); tmp="$here/.v1-$$.sh"
trap 'rm -f "$tmp"' EXIT
sed '2i # windows: ok' "$here/test-migration.sh" > "$tmp"
bash "$tmp" v1 < /dev/null
