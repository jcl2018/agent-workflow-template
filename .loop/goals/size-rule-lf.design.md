# size-rule-lf design

Problem: health's scripts size rule (health.py size_rows) used os.path.getsize, skill-lines (rules.py) counted text lines, and package.py's Scripts rule used raw bytes. On a Windows CRLF checkout the sizes read over the cap, so 11 scripts under 20,480 bytes in git failed (issue 3125).

Approaches: (A) normalize CRLF to LF in the bytes each rule reads (no git dependency, works for staged and unstaged edits); (B) `git cat-file -s :path` (needs a repo and an index, wrong for a package checked outside git).

Chosen: A. Size uses len(bytes.replace(b"\r\n", b"\n")); skill-lines counts the LF-normalized splitlines. package.py keeps its `>= 20 KB` rule. No new files under skills/; the three edited scripts stay far under the cap.

Done lines: (1) a toy test builds CRLF files and checks the three rules; row size-lf-crlf, seen red. (2) no new skills files, scripts under 20,480.

Open questions: none.
