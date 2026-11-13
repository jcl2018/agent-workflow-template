# release-bump-docs plan

1. release.py auto_need: read the recorded bump before the docs-only check (done).
2. Toy cases docsbump and docspatch in test-delivery-release.sh, rows del5-docs-bump-minor and del5-docs-patch-default (done).
3. Tests tables re-rendered; wiki current.
4. Verify: the Linux lane runs the toy cases; locally auto_need was run on a docs-only temp repo: no bump gives leave, a minor sidecar gives minor.
Risk: the toy script is skipped on Windows, so the lane on Linux is the proof.
