# release-bump-docs design

Problem: release.py auto_need returns leave for a docs-only diff before it reads the owner's recorded bump, so a docs-only goal released a patch whatever goal.py set recorded (#3787); v1-format came out v0.27.58, not v0.28.0.

Approaches: (1) read the recorded bump first and let it win on any goal; (2) special-case docs-only goals in need_of. Chosen: (1), one place, and a goal with no recorded bump still leaves/patches.

Done line: a docs-only goal with a recorded minor bump releases a minor; with none, a patch. Tests: two toy cases and DEL-5 rows.

Open questions: none.
