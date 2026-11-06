#!/bin/bash
# Build a throwaway toy repo with a bare origin. usage: make.sh DIR  -> DIR/repo, DIR/origin.git
set -e
here=$(cd "$(dirname "$0")" && pwd); d=$1; mkdir -p "$d"
git init -q --bare -b main "$d/origin.git"
cp -R "$here/repo" "$d/repo"; cd "$d/repo"
git init -q -b main; git config user.email t@example.test; git config user.name Toy
git add -A; git commit -qm "Toy repo"; git remote add origin "$d/origin.git"; git push -q -u origin main
