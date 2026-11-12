# private-size-pc design

Problem: private.py is 21,767 bytes in git, over the 20,480-byte script cap (v0.27.31 only grows it).

Approaches: (A) drop comments and docstrings, shorten the usage prose; no code touched, risk none, saves about 1.4 KB. (B) split code into a new file; the package is capped on file count, so rejected.

Chosen: A. The usage line (`__doc__.splitlines()[5]`) keeps its position. Result 20,348 bytes in git.

Done line: size verified with git cat-file; the rows that cover private.py are toy shell tests that skip on Windows ('# windows: ok' missing), so they skip with their reason.

Open questions: none.
