# Design: a pull request whose merged head breaks the package fails its lane (DEL-5, SET-3)

## Problem
dev/package.py gives the verdict on the package, but the only row that runs it (`package-passes`) skips on native
Windows, so a lane run there never saw scripts grow past 20,480 bytes or the file count pass 99 (#3800).

## Approaches
1. Run dev/package.py itself from a new lane step. It shells out and gives other verdicts on Windows, and the lane
   code lives under skills/, which ships to repos that have no dev/package.py.
2. A Python toy that imports dev/package.py and calls its own `walk`, `check_files` and `check_scripts` on the tracked
   files of the checkout, with controls on a small synthetic package. Two land rows run it; no new file under skills/.

## Chosen
Approach 2: it reuses package.py's checks (nothing duplicated), runs on Windows, and the rows are picked first when a
skills file changes because the toy declares `# reads: dev/package.py skills/`.

## Done line
The PR lane fails when a script is over 20,480 bytes or the package has over 99 files, and passes on main:
`package-gate-head` (seen red with a script grown past the cap) and `package-gate-controls` (seen red with the caps raised).

## Open questions
None.
