#!/bin/bash
# Build a throwaway toy repo with a bare origin. usage: make.sh DIR  -> DIR/repo, DIR/origin.git
set -e
export LOOP_NO_GIT_HOOKS=1  # no toy installs git hooks (guard-enforce); reap.sh exports it for the tests
here=$(cd "$(dirname "$0")" && pwd); d=$1; mkdir -p "$d"
git init -q --bare -b main "$d/origin.git"
cp -R "$here/repo" "$d/repo"; cd "$d/repo"
git init -q -b main; echo "__pycache__/" >> .git/info/exclude; git config user.email t@example.test; git config user.name Toy
git add -A; git commit -qm "Toy repo"; git remote add origin "$d/origin.git"; git push -q -u origin main
# A wiki with one page this tool didn't write, as a real repo's wiki would have.
git init -q --bare -b main "$d/origin.wiki.git"
git init -q -b main "$d/seed"; cd "$d/seed"; git config user.email t@example.test; git config user.name Toy
echo "# Written by someone else" > Home.md; git add -A; git commit -qm "First page"
git remote add origin "$d/origin.wiki.git"; git push -q origin main
# A stand-in skill flow for the tests: each "skill" prints STEP: done, and the probe proves the unattended env.
cd ..
printf '#!/bin/bash\nprintf "%%b\\n" "${FAKE_SKILL_OUT:-DEPTH: full\\nSTEP: done}"\n' > skill.sh
python3 -c "
import json, sys
d = sys.argv[1]
json.dump({'command': ['bash', d + '/skill.sh'], 'env': {'FAKE_MODE': 'unattended'}, 'probe': ['bash', '-c', 'echo \$FAKE_MODE'],
           'probe_expect': 'unattended', 'steps': {s: 'stand-in-' + s for s in ('idea', 'plan', 'review', 'qa', 'ship')}},
          open(d + '/flow.json', 'w'))" "$(pwd)"
