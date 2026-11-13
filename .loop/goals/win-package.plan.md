# Plan: win-package

Checked against the code: `walk`, `read`, `frontmatter`, `check_scripts`, `private_prefixes`, `check_pack` and
`manifest` in `dev/package.py` all exist and are the only places that touch paths, bytes, files or subprocesses.

## Build steps

1. `walk`: return every path with `/` (`relpath(...).replace(os.sep, "/")`).
2. `read`: for data that decodes as UTF-8 and has no NUL, replace `\r\n` with `\n`, so sizes, hashes, the ZIP and the
   frontmatter regex see the bytes git stores.
3. `open` in `private_prefixes` and `check_pack`: `encoding="utf-8"`. `manifest`'s git call and the `--help` runs:
   `encoding="utf-8", errors="replace"`.
4. `check_scripts`: copy each scripts folder once, run each script `-E -s -X utf8 SCRIPT --help` with
   `stdin=subprocess.DEVNULL` and `timeout=30`; a timeout fails as `does not run alone: timed out after 30s`.
5. Test `dev/toy/test-package-win.sh` with cases `parity` and `no-stdin`, and regression rows of category defect linked to
   issue #1397, seen red on the old package.py.

## Tests per done line

1. `parity`: copy the shipped tree twice, one in CRLF; plant in both a script whose `--help` prints non-ASCII; run
   package.py on each under `PYTHONUTF8=0 PYTHONCOERCECLOCALE=0 LC_ALL=C`; the sorted FAIL lines must be equal. Old code:
   CRLF copy reports "no SKILL.md" and oversize scripts, and the ASCII parent raises UnicodeDecodeError.
2. `no-stdin`: plant a script whose `--help` reads stdin; run package.py with an open pipe on stdin under a 120 s bound;
   it must finish. Old code: blocks until the bound.

## What could break

A file committed with CRLF would be counted as LF (none today). The per-folder copy shares one temp folder between a
folder's scripts; `--help` writes nothing, so they cannot affect each other. Linux output is unchanged except that `/`
was already the separator.

## Out of scope

The current Linux failures on main (103 files, `automation` not in listing.commands): they fail on both platforms, so the
verdicts already agree there. Executable-bit detection on Windows.
