# doc-fixes-v1 design

Problem: README says health runs in GitHub Actions (AUT-3: it runs on the Mac); 7 depth-* rows link DEL-1 but test DEL-6 (#405); Monitoring titles are whole sentences (#410); adopt-set-3 checks only version, skills and size (#414).

Chosen: README rows 119, 120 and the prose paragraph rewritten (regression in Actions for a public repo, health on the Mac). The 7 depth-* rows linked DEL-1 relinked to DEL-6; the 5 others link MON-4, DEL-4 and SET-2 correctly (each tests a different requirement) and stay. adopt-set-3 gains: unzip the package, copy skills as an install, compile every script and run setup.py --dry-run from the copy. Short titles drafted in DECISIONS.md under "Waiting on owner un-review", not applied (titles locked).

Not done here: the generated Automation table (counting.py) still lists health.yml "not deployed"; that is code, left as a follow-up. adopt-set-3 red proof needs a Linux runner (the toy skips on Windows, package.py fails on os.getuid).

Open questions: none.
