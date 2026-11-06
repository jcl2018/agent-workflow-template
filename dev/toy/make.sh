#!/bin/bash
# Build a throwaway toy repo with a bare origin. usage: make.sh DIR  -> DIR/repo, DIR/origin.git
set -e
here=$(cd "$(dirname "$0")" && pwd); d=$1; mkdir -p "$d"
git init -q --bare -b main "$d/origin.git"
cp -R "$here/repo" "$d/repo"; cd "$d/repo"
git init -q -b main; git config user.email t@example.test; git config user.name Toy
git add -A; git commit -qm "Toy repo"; git remote add origin "$d/origin.git"; git push -q -u origin main
# A wiki with one page this tool didn't write, as a real repo's wiki would have.
git init -q --bare -b main "$d/origin.wiki.git"
git init -q -b main "$d/seed"; cd "$d/seed"; git config user.email t@example.test; git config user.name Toy
echo "# Written by someone else" > Home.md; git add -A; git commit -qm "First page"
git remote add origin "$d/origin.wiki.git"; git push -q origin main
