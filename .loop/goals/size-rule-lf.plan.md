# size-rule-lf plan

Files (confirmed): skills/workflow-health/scripts/health.py size_rows; skills/workflow-health/scripts/rules.py skill_lines; dev/package.py check_scripts; new dev/toy/test-size-lf.sh; .loop/regression.tsv row size-lf-crlf.

Steps: 1. LF-normalize bytes in the three rules (done, c1714c20). 2. Toy test with CRLF fixtures (149/150-line SKILL.md, 20,100-byte script). 3. Defect row, seen red (also checked by hand that the test fails with the fix removed).

Tests: size-lf-crlf for done line 1; size-budget and health's own scripts rule for done line 2 (edited scripts: health.py 17,765, rules.py 18,502, package.py 14,124 bytes in git).

Could break: package.py's `>= 20 KB` threshold unchanged. Out of scope: package.py's os.getuid failure on Windows (win-posix-rest).
