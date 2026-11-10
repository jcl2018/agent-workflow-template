# Plan: narrow-rows

Source: `.loop/goals/narrow-rows.design.md` (spec review: 3 rounds, blocking findings fixed, minor concerns resolved
below). Done lines: `.loop/goals/narrow-rows.md`.

## Implementation plan

1. `skills/workflow-regression/scripts/lanes.py`: declarations and the narrow closure. Public API unchanged
   (`closure(root, command, cache)` still returns `(deps, always)`; `plan()` signature unchanged).
   - `READS = re.compile(r"^#\s*reads:\s*(.+)$", re.M)`, read from the whole file. Several lines add up.
     `declared(root, rel, cache)` returns `(paths, problem)`. A word containing `$`, `*` or `?`, an absolute path, or a
     path that does not exist on disk is a problem (`declared path <p> does not exist`).
   - `exact(root, text, folder)`: like `references()`, but no `widen()` and no `SKILL_NAME` words. Returns files,
     folders and whether it names the bare `$here/skills` tree. Candidates are tried as written and joined to the
     file's own folder (toy scripts use `$here` = repo root; `make.sh` uses `$here` = `dev/toy`).
   - `narrow_scan(root, rel, cache)`, per file, once per plan:
     - `.sh` and files without an extension: `exact()` over the text (sourced files are named files, so `. dev/lib.sh`
       is covered).
     - `.py`: same-folder imports (today's `IMPORT` rule) and every quoted literal ending in a file extension
       (`py md json sh tsv txt yml yaml toml`), taken by base name: the union of every file with that base name in the same
       skill folder, anywhere under `skills/`, and in the file's own folder.
     - anything else: a leaf (no scan).
   - `narrow(root, seeds, cache)` returns `(deps, why)`. Work list from the seeds; each reached file adds its
     `narrow_scan` files, its non-skill folders as prefix dependencies (walked for further files, as `closure()` does
     now), its skill folder mentions (recorded, not walked), its bare-tree flag and its `# reads:` paths (declared
     folders are prefixes and walked). When the list empties, apply the base-name rule: for every recorded skill
     folder, each file in it whose base name appears in the text of any reached `.sh` (or extension-less) file becomes
     a dependency and is followed; repeat until nothing is added.
     `why` is set (first reason wins) when: a declaration has a problem; a recorded skill folder contains no declared
     path and no declared path is a prefix of it (`names <folder> but declares no file in it`); the bare tree is named
     and `skills/` is not declared (`names all of skills/ but does not declare skills/`).
   - `closure(root, command, cache)`: the command's own exact files are found first. If none of them has a
     `# reads:` line, today's code path runs unchanged (wide). Otherwise: seeds = each named file that has a `# reads:` line, plus its declared paths (the script's own text
     is scanned too); the narrow
     closure of the seeds; then every named file the narrow closure did not reach adds its own wide closure (today's
     algorithm applied to that one path). The command's own `ROOT` (whole repo) and no-path rules still give
     `always`. A `why` makes the row `always`, and the reason is kept in `cache[("why", command)]`.
   - `plan()`: an always row with a reason appends `ALWAYS <id>: <reason>` to `notes`. Notes print only when `plan()`
     runs (a reuse run with a usable record and no FAIL rows); a FULL run already runs every row, so it needs none.
     `regression.py` is not touched.
   - `affected(root, rows, paths, cache)` and `python3 lanes.py affected [--level L] PATH...` (a `__main__` block;
     the docstring says it is also runnable). It reads `.loop/regression.tsv` from the repo it runs in (rows by id,
     level, command), and decides each row against the given paths with plan()'s per-path rules, minus the parts that
     need a record: `NO_EFFECT` paths rerun only rows naming them (`named()`), `.loop/regression.tsv` reruns rows that
     reach `regression.py`, any other path reruns rows whose closure hits it, and a path no row hits prints
     `UNMAPPED <path>: full run` and counts every row. Output: `AFFECTED n of m rows (ids)` plus one `ALWAYS` line per
     always row. Read-only. The shared per-path decision moves into one helper both `plan()` and `affected()` call.
   - lanes.py stays under 20 KB (10.6 KB now; budget about 5 KB).
2. `# reads:` headers in every `dev/toy/*.sh` that a row in `.loop/regression.tsv` names (29 scripts). Each lists the
   skill scripts and data files the script runs, never a skill `scripts/` folder. Folder declarations only where the
   script really reads a whole folder (`skills/` for `cp -R "$here/skills"`; a skill's `scripts/` copied with `cp -R`
   is declared by the files the copy then runs, and the copy's literal names are followed by the closure). The build
   checks each script's `$here/skills` uses and computed names by hand (`for f in watch board board_page ... $f.py`,
   health and milestone size loops) and declares those files. Helpers (`make.sh`, `ci-env.sh`, `fakegh/`,
   `flow-done.sh`, `run-goal.sh`) get no header; they are followed.
3. `dev/toy/test-lanes.sh`: a new section in the `regression` part, in its own toy repo layout with a `skills/` tree
   of two fake skills (`skills/a/scripts/a.py`, `skills/a/scripts/data.md` named by a.py as `"data.md"`,
   `skills/b/scripts/b.py`, `skills/b/scripts/helper.py` imported by b.py, `skills/b/scripts/solo.py` that nothing
   imports or names in quotes), a shared `dev/common.sh` every script sources, a folder `tools/` with `tools/x.txt`,
   and these scripts, one row each:
   - `ta` declares `skills/a/scripts/a.py`. `tb` declares `skills/b/scripts/b.py`. `tm` sources its own helper
     `dev/tm-lib.sh` (no other script sources it), which sets `m=skills/b/scripts`; tm runs `$m/b.py` and
     `$m/solo.py` and declares only b.py. `tx` declares a missing path. `tf` declares a.py and names
     `skills/b/scripts` without declaring a file in it. `tu` has no header and names `skills/a/scripts/a.py` (wide:
     today's `widen()` makes that all of `skills/a/`). `th` declares `skills/a/scripts/data.md` and reads
     `tools/x.txt` through the undeclared folder `tools/`.
   - Always rows: tx and tf, on every change, each printing an `ALWAYS <id>: <reason>` note.
   - Exact rerun sets, compared for equality on the row ids (always rows included):
     a.py → ta, tu, tx, tf. data.md → ta, th, tu, tx, tf. helper.py → tb, tm, tx, tf. solo.py → tm, tx, tf.
     dev/common.sh → every row. tools/x.txt → th, tx, tf. A new file no row's closure reaches (`src/z.txt`) → UNMAPPED full
     run (today's rule, unchanged).
   - `lanes.py affected <path>` on the toy repo gives the same row ids in its `AFFECTED` line for each path above.
4. Rows in `.loop/regression.tsv` (goal REG-6, category criterion, descriptions as Given/When/Then), each seen
   failing once with `regression.py red <id> --break` and passing:
   - `lanes-headers` (done 1): every `dev/toy/*.sh` a row of this repo names has a `# reads:` header and declares
     no skill `scripts/` folder (the CEO-accepted coverage check).
   - `lanes-declared` (done 1): a declared script's rows rerun on a change to a declared file and not on a change to
     another skill's file (ta/tb sets above).
   - `lanes-folder-var` (done 1, narrowing safety): an undeclared file used through a folder variable set in another
     file still reruns its row (solo.py → tm).
   - `lanes-repo-narrow` (done 2): on this repo, `lanes.py affected skills/workflow-health/scripts/judge.py` reruns
     fewer than half of the land rows, and every rerun row that is not an always row reaches judge.py through the
     closure of a toy script whose `# reads:` header declares a file of `skills/workflow-health/` directly. Cross-skill
     paths are computed, not grepped: the build runs `lanes.py affected` on judge.py once, and every rerun row that
     is neither an always row nor a workflow-health row is listed as cross-skill in the PR table and excluded from
     the check by id.
   - `lanes-always` (done 3): a row whose declaration cannot be resolved reruns on a mapped change that does not touch it: tools/x.txt
     → th, tx, tf, with tx and tf in the set and ta and tb not.
   - `lanes-narrow-wide` (done 4): a narrow change reruns only its rows (solo.py set); a change to a file every row
     reaches reruns all (dev/common.sh).
5. `criteria.py render` rewrites `docs/wiki/Regression.md`'s Tests under REG-6 from those rows (done 5). No hand edit
   of the Tests section.
6. Docs: `skills/workflow-regression/SKILL.md` and `references/commands.md` get the `# reads:` rule and the
   `lanes.py affected` command (a few lines; regression-summary edits the same files, so keep the edits local).
   `docs/wiki/Regression.md` REG-6 requirement text is unchanged.
7. Measurement for the PR (done 2): a table from `lanes.py affected` on this repo, before (main's lanes.py) and after,
   for every script file under `skills/`, plus one code-plus-docs change (`health.py` with `skills/workflow-health/SKILL.md`)
   to show the UNMAPPED effect honestly. Counts come from the table itself (the v0.13.1 table has 164 land rows).

### Known limits, stated

- Files no row reads become UNMAPPED full-run triggers after narrowing: SKILL.md files, `references/*.md`,
  `skills/design-guide.md`, `skills/loop-files.md`, `docs/wiki/` pages, scripts no row reaches and `dev/toy` files no
  row names. A goal that changes those with code still gets a full run. Out of scope here; the measurement shows it.
- Paths built at run time inside `.py` files: the known cases (`seed.py` `tool(repo, "workflow-docs", "prd.py")`,
  `operate.py` `script("watch.py")`, `health.py` `sibling("workflow-regression", "regression.py")`) carry literal
  file names and are caught. A script whose target name is computed must declare that target by hand.
- "Belongs to" (done 2): a non-always row belongs to a skill when a toy script it names declares a file of that skill
  directly in its `# reads:` header. Item 4's `lanes-repo-narrow` uses exactly this definition.


<!-- autoplan-accepted:ceo -->
- Header coverage check: a case in `dev/toy/test-lanes.sh` (regression part) reads `$here/.loop/regression.tsv`
  (the real repo root that test-lanes.sh resolves as `$here`), and for every `dev/toy/*.sh` a row names asserts it has
  at least one `# reads:` line and that no declared path is a skill `scripts/` folder (`skills/<s>/scripts/`). Its PASS
  line backs a new REG-6 row `lanes-headers` (done 1), seen failing once (a header removed) and passing, and rendered
  by item 5.
- `dev/toy/test-lanes.sh` gets its own header: `skills/workflow-regression/scripts/regression.py`,
  `skills/workflow-regression/scripts/lanes.py`, `skills/workflow-setup/scripts/setup.py`,
  `skills/workflow-delivery/scripts/goal.py`, `skills/workflow-delivery/scripts/flow.py`,
  `skills/workflow-delivery/scripts/role.py`.
- Read-trace completeness check (both CEO voices, finding "nothing checks that a declaration is complete"):
  `dev/toy/check-reads.sh [SCRIPT...]` runs each named toy script (default: every `dev/toy/*.sh` a land row names)
  once with `PYTHONPATH` pointing at a temporary `sitecustomize.py` whose `sys.addaudithook` logs every `open` and
  `cpython.run_file` path inside the repo's `skills/` tree to a trace file. It then asks
  `python3 lanes.py deps '<row command>'` for the union of the script's rows' closures and fails, naming the script
  and each file, when a traced skill file is outside that union. Coverage limit, stated in its header: Python reads
  only (bash `cat`/`grep` of skill files are covered by the static scan of the script text). `lanes.py deps COMMAND`
  prints the row's dependency set, one path per line, plus `ALWAYS: <reason>` when the row is always. A nightly row
  `lanes-trace` (REG-6, done 3) runs it, seen failing once (a declaration removed from one script) and passing; the
  build also runs it once over all 29 scripts before qa and fixes every header it flags.
- Fail-wide resolution rules (native CEO findings 5-6): quoted literal names in `.py` resolve to the union of every
  match (same skill folder, anywhere under `skills/`, own folder), never the first only; `# reads:` lines are read
  from the whole file, not the first 40 lines; a bare word `skills` used as a path after `cd "$here"` (as in
  `cp -R skills`) counts as the whole tree, like `$here/skills`; the base-name rule matches the file name with its
  extension (`board.py`), and a name built at run time must be declared.
- `lanes-headers` also fails when any header has a declaration problem (a missing or unresolvable path).
- A declared path whose normalized form leaves the repo root (absolute, or `..` escaping it) is a declaration
  problem (CEO section 3).
- Measurement (both voices): item 7's table adds (a) the floor: the rows that declare all of `skills/` and so rerun on
  every skill change, listed with their count; (b) `lanes.py affected` over the file lists of the last 15 merged
  goal PRs on main, before and after, as rows rerun and as row-seconds rerun (weighted by each row's seconds in the
  newest branch record under the git common dir's `loop/tests/`), with the median, and how many came out UNMAPPED.
<!-- /autoplan-accepted:ceo -->

<!-- autoplan-accepted:dx -->
- Header grammar: a line `# reads: <path> [<path>...]` at column 0, anywhere in the file; paths are repo-relative,
  separated by whitespace, unquoted; a trailing `/` marks a folder; nothing else on the line. `# reads: skills/` is
  the documented per-script opt-out (stay wide). Headers are required on every `dev/toy/test-*.sh` that a row names;
  wrappers such as `ci-env.sh`, `make.sh` and `fakegh/` are exempt and followed.
- `python3 lanes.py check [SCRIPT...]` (default: every `dev/toy/test-*.sh` a row of this repo names) validates
  headers statically and runs the narrow closure per script, reporting every problem, not the first only, as
  `<CODE> <script>:<line>: <what>` with a last line `fix: <the line to add or change>`. Codes:
  `LANES-DECL-MISSING` (path does not exist), `LANES-DECL-PATTERN` (`$`, `*`, `?` in a path), `LANES-DECL-ESCAPE`
  (absolute or leaves the repo), `LANES-DECL-FOLDER` (names a skill folder, declares no file in it),
  `LANES-DECL-TREE` (names all of skills/ without declaring `skills/`), `LANES-DECL-NONE` (a test script with no
  header). Exit 0 clean, 1 problems, 2 usage. `lanes-headers` runs `lanes.py check` on this repo.
- CLI contract for `affected`, `deps` and `check`: the repo root is `git rev-parse --show-toplevel` of the current
  directory, overridden by `--root DIR`; PATH arguments are normalized to repo-relative and a path outside the repo
  is a usage error; `--level land|nightly|all` (default `land`, matching `regression.py run land`); results on
  stdout, sorted, one fixed-prefix line each (`AFFECTED n of m rows (id, id, ...)`, `UNMAPPED <path>: full run;
  no row reads it (add it to a script's # reads: if one should)`, `ALWAYS <id>: <reason>`); usage errors on stderr
  with exit 2 (no table under the root, unknown level, no PATH, unknown subcommand); unexpected errors print one
  line naming the file and row and exit 1, with the full trace only under `LANES_DEBUG=1`. `deps COMMAND` prints
  dependency paths sorted, then `ALWAYS <command>: <reason>` lines; `deps COMMAND --why PATH` prints the reach chain
  from the command to PATH (`dev/toy/t.sh -> skills/a/scripts/a.py -> skills/a/scripts/data.md`), or `NOT REACHED`.
  `affected` is documented as dependency impact, not an exact preview: it has no record, so FAIL rows, ancestry and
  edited rows are outside it.
- `check-reads.sh` invocation contract: it groups the rows of the selected scripts by their invocation (the command
  up to the first `|`, wrappers and arguments kept, e.g. `bash dev/toy/ci-env.sh bash dev/toy/test-docs.sh`) and runs
  each distinct invocation once from the repo root, in a `mktemp -d` dir removed by a trap; the sitecustomize hook
  writes a start marker per Python process; a traced path containing `/skills/<s>/<rest>` under any directory is
  mapped back to `skills/<s>/<rest>` when that repo file exists (copied trees); it fails when an invocation exits
  non-zero (exit code and the last 5 stderr lines), when an invocation that runs Python left no marker
  (`LANES-TRACE-NOHOOK: PYTHONPATH reset or -I/-S?`), or when a traced skill file is outside the union of those rows'
  closures (`LANES-TRACE-UNDECLARED <script> <file>` plus `fix: # reads: <file>`). Python reads only, stated.
- `LANES_WIDE=1` in the environment makes `closure()` take the wide path for every row (documented as the first step
  when a narrowed lane is suspected of missing a row).
- Docs (regression SKILL.md and references/commands.md, under their own new headings): the grammar with a
  copy-paste example, the closure rules in five lines, a reason→fix table with the codes, `affected`/`deps`/`check`
  usage with sample output, the opt-out, `LANES_WIDE=1`, the coverage limit of check-reads, a three-step walkthrough
  for a new test script (write the header, `lanes.py check <script>`, `lanes.py affected <file>`; register rows with
  `regression.py add ... --level land`), and the migration note (headerless scripts keep the wide mapping; the first
  run after lanes.py changes is FULL because records carry the runner hash).
- Replacements of earlier text (this block wins where they differ): `check-reads.sh` runs each distinct row
  invocation once, not each script bare; `deps` prints `ALWAYS <command>: <reason>`, not `ALWAYS: <reason>`; the
  header coverage check (`lanes-headers`, item 4 and the CEO block) applies to `dev/toy/test-*.sh` entry points a row
  names, not to wrappers such as `ci-env.sh`; `lanes-headers` asserts `lanes.py check` exits 0 on this repo.
<!-- /autoplan-accepted:dx -->

<!-- autoplan-accepted:eng -->
- Scanner (E1): `exact()` and the bare-tree test accept `$here/`, `${here}/`, `"$here"/` and `"${here}"/` path
  forms; a path in script text containing `*` or `?` counts as its static prefix folder (the part before the first
  glob character, cut back to a `/`): a skill folder becomes a recorded skill-folder mention, `skills/` a bare-tree
  mention, anything else a prefix dependency. `exact()` and `references()` share one implementation with a `widen`
  flag.
- Backed folder declarations (E2): declaring a skill folder (`skills/<s>/scripts/` or `skills/<s>/`) is allowed when
  the declaring script's text globs or recursively reads that folder; otherwise `lanes.py check` reports
  `LANES-DECL-FOLDER-UNBACKED` and the row is always. The header coverage rule bans only unbacked folder
  declarations. Size-loop files are covered by the backed folder, not listed by hand.
- Narrow-branch semantics (E3, Codex 5): the command's own files, directories, bare-tree flag and ROOT are kept as
  today before narrowing; a reached file's `cd "$here"` or bare `$here` adds nothing (as today), and its whole-tree
  forms are caught by the scanner rule above.
- Python follow (E6): a quoted literal in a reached `.py` that resolves to an existing folder in the same skill is a
  folder dependency (walked).
- Header placement (E10, replaces "read from the whole file"): `# reads:` lines are read from the leading comment block
  (after an optional shebang, consecutive lines starting with `#`); a `# reads:` line at column 0 anywhere else is
  `LANES-DECL-PLACE` and the row is always.
- Base-name rule (E11): word-bounded match of the file name with extension; files are matched recursively under each
  recorded skill folder.
- Deletions (Codex 1): in `plan()`, a deleted or renamed path under `skills/` or `dev/` since the recorded commit
  (`git diff --name-status`) forces FULL (`FULL: deleted <path>`); `affected` prints `DELETED <path>: full run`.
  Test: delete a helper imported by one row while another row declares `skills/`.
- check-reads.sh (Codex 3, 4, 6, E4, E13, replaces the invocation-grouping rule): it runs each row's exact command
  (identical commands once) from the repo root in its own process group with a 600 s timeout (descendants killed),
  with `PYTHONPATH=<tmp>:$PYTHONPATH`, a `python3`/`python` shim first on PATH that logs every launch and execs the
  real interpreter, and a sitecustomize audit hook logging `open`, `cpython.run_file`, `os.listdir`, `os.scandir` and
  `glob.glob`; it fails per row on a non-zero exit, on launches without a matching hook marker
  (`LANES-TRACE-NOHOOK`), or on a traced skill file or listed skill folder outside that row's closure
  (`LANES-TRACE-UNDECLARED`); reads outside the repo are mapped to repo skill files by content hash (renamed and flat
  copies); realpath is used for every path. Fixtures: a hooked setup process plus an unhooked `python3 -I` child, and a
  renamed and a flat copy.
- Parity guard (E7): a test-lanes case runs `lanes.py affected` with and without `LANES_WIDE=1` on a toy repo with no
  headers and requires identical output; every existing test-lanes check passes unchanged.
- lanes-repo-narrow (E8, Codex 7, replaces the exclusion-by-id rule): reruns fewer than half the land rows, includes
  every row whose named test script declares a `skills/workflow-health/` file (no missing rows), and prints each
  other non-always row with its `deps --why` chain for the PR table.
- CLI module (E9): `affected`, `deps` and `check` live in `skills/workflow-regression/scripts/lanes_cli.py`, which
  imports lanes; lanes.py keeps the mapping and stays under 20 KB.
- Measurement (Codex 8): the before column comes from a pinned copy of main's lanes.py at the merge base run through
  the same harness; the row population is the PR branch's table; rows without a recorded duration are counted and
  reported as unknown, never zero; the PR also reports `affected` wall time.
<!-- /autoplan-accepted:eng -->
## Review record

The plan step runs /autoplan unattended in the worker session (2026-11-09): CEO (SELECTIVE EXPANSION), DX and Eng
phases; no UI scope, so the design phase is skipped. Each phase has a native reviewer and the Codex outside voice.

### CEO phase, Step 0

- Premise (0A): the real problem is that a reuse lane on this repo never narrows: any skill change reruns all 164 land
  rows (about 1,450-1,590 s of row time per lane, measured from three branch records under the git common dir's
  `loop/tests/`). The plan fixes the cause directly (folder widening in lanes.py and folder-named toy scripts), not a
  proxy. Doing nothing keeps every ship and pr lane after a code change at full cost.
- Leverage (0B): `references()`, `scan()`, `walk()`, `closure()`, `hits()`, `named()` and `plan()` in lanes.py are
  reused; the narrow path is added beside the wide one, which stays the fallback.
- Dream state (0C): CURRENT all-or-nothing lane -> THIS PLAN cost proportional to the change for declared rows, with
  reasons printed -> 12-MONTH IDEAL every row narrow, docs-only and code-plus-docs changes mapped, declarations checked
  automatically.
- Mode (0E): SELECTIVE EXPANSION (autoplan override). No new approach decision was needed: the design's Approach A
  stands.
- Scope (0G): see the CEO plan `ceo-plans/2026-11-09-narrow-rows.md` in the private review folder. Accepted: header
  coverage check. Deferred: header suggester, no-effect docs. Skipped: per-row declarations, per-row lane output.

0H spec review round 1 (6/10): all eleven findings accepted as mechanical fixes. Round 2 (6/10): eight of nine
round-1 issues resolved; its new findings (exact rerun sets with always rows, one belongs-to definition, the
test-lanes.sh header list, lanes-folder-var mapped to done 1, the AFFECTED-line comparison) accepted and applied in
the baseline edits below. Round 3 (8/10, cap reached): its three one-line fixes (UNMAPPED wording, computed
cross-skill rows, lanes-always pinned to a mapped change) applied; issues verified: 3 of 3 (applied text present).
The cosmetic duplicate of lanes-headers between item 4 and the accepted block stays (the block is appended by the
review tool).

0H document approval: auto-decided A (approve the CEO plan and working plan as they stand) under /autoplan's
recommended-option rule; this approves the documents only.

0I temporal interrogation (human team / CC):
- Hour 1, foundations: how `references()` resolves `$here` paths (as written and joined to the file's folder), what
  `walk()` returns, and that `closure()`'s cache is keyed by command. Human ~1h / CC ~5 min.
- Hours 2-3, core logic: the narrow work list and the base-name fixpoint; first-reason-wins for `why`; keeping the
  wide path byte-for-byte when no named file has a header. Ambiguity: a declared folder (`dev/toy/repo/`) is walked
  like a non-skill folder. Human ~3h / CC ~20 min.
- Hours 4-5, integration: 29 headers; computed names in loops (`$f.py`) declared by hand; `cp -R` of a skill scripts
  folder; the always rows' notes in `plan()`. Surprise: `make.sh` copies `dev/toy/repo/` whole, so every row that
  runs make.sh depends on that folder. Human ~4h / CC ~30 min.
- Hours 6+, tests: the toy section's exact sets, five new rows red then green, the repo measurement. Human ~4h /
  CC ~30 min.
- Feasibility blockers: none found. Pending choices: none.


<!-- autoplan-baseline-edits:ceo {"sourceSha256":"a870619440b0355bbc1ebfe6ae5fddf6662e729cf99d95bbabff817228e516c9","replacements":[{"oldText":"Otherwise: seeds = the declared named files;","newText":"Otherwise: seeds = each named file that has a `# reads:` line, plus its declared paths (the script's own text\n     is scanned too);"},{"oldText":"3. `dev/toy/test-lanes.sh`: a new section in the `regression` part, in its own toy repo layout with a `skills/` tree\n   of two fake skills (`skills/a/scripts/a.py`, `skills/b/scripts/b.py`, `skills/b/scripts/helper.py` imported by\n   b.py, `skills/a/scripts/data.md` named by a.py as `\"data.md\"`), a shared `dev/common.sh` every script sources, and\n   these scripts and rows:\n   - `dev/ta.sh` declares `skills/a/scripts/a.py`; `dev/tb.sh` declares `skills/b/scripts/b.py`; `dev/tm.sh` sets\n     `m=skills/b/scripts` in a sourced helper and runs `$m/b.py` and `$m/helper.py` but declares only b.py;\n     `dev/tx.sh` declares a missing path; `dev/tf.sh` declares a.py and names `skills/b/scripts` without declaring a\n     file in it; `dev/tu.sh` has no header and names `skills/a/scripts/a.py` (wide, today's rule); `dev/th.sh` reads\n     `tools/x.txt` through an undeclared folder `tools/`.\n   - Checks: a change to `a.py` reruns only the rows reaching it (ta, tu, tf by its always reason, tx); a change to\n     `data.md` reruns ta (quoted name); a change to `helper.py` reruns tb (import) and tm (folder-variable base name,\n     set in another file); a change to `dev/common.sh` reruns every row (wide); a change to `tools/x.txt` reruns th\n     (non-skill folder kept); an unrelated change still reruns tx and tf (always) and they print `ALWAYS` notes; the\n     undeclared tu still reruns on a change to any file in skill a (wide fallback).\n   - `lanes.py affected` on the toy repo prints the same sets.\n","newText":"3. `dev/toy/test-lanes.sh`: a new section in the `regression` part, in its own toy repo layout with a `skills/` tree\n   of two fake skills (`skills/a/scripts/a.py`, `skills/a/scripts/data.md` named by a.py as `\"data.md\"`,\n   `skills/b/scripts/b.py`, `skills/b/scripts/helper.py` imported by b.py, `skills/b/scripts/solo.py` that nothing\n   imports or names in quotes), a shared `dev/common.sh` every script sources, a folder `tools/` with `tools/x.txt`,\n   and these scripts, one row each:\n   - `ta` declares `skills/a/scripts/a.py`. `tb` declares `skills/b/scripts/b.py`. `tm` sources its own helper\n     `dev/tm-lib.sh` (no other script sources it), which sets `m=skills/b/scripts`; tm runs `$m/b.py` and\n     `$m/solo.py` and declares only b.py. `tx` declares a missing path. `tf` declares a.py and names\n     `skills/b/scripts` without declaring a file in it. `tu` has no header and names `skills/a/scripts/a.py` (wide:\n     today's `widen()` makes that all of `skills/a/`). `th` declares `skills/a/scripts/data.md` and reads\n     `tools/x.txt` through the undeclared folder `tools/`.\n   - Always rows: tx and tf, on every change, each printing an `ALWAYS <id>: <reason>` note.\n   - Exact rerun sets, compared for equality on the row ids (always rows included):\n     a.py → ta, tu, tx, tf. data.md → ta, th, tu, tx, tf. helper.py → tb, tm, tx, tf. solo.py → tm, tx, tf.\n     dev/common.sh → every row. tools/x.txt → th, tx, tf. A new file no row's closure reaches (`src/z.txt`) → UNMAPPED full\n     run (today's rule, unchanged).\n   - `lanes.py affected <path>` on the toy repo gives the same row ids in its `AFFECTED` line for each path above.\n"},{"oldText":"4. Rows in `.loop/regression.tsv` (goal REG-6, category criterion, descriptions as Given/When/Then), each seen\n   failing once with `regression.py red <id> --break` and passing:\n   - `lanes-declared` (done 1): a declared script's rows rerun on a change to a declared file and not on a change to\n     another skill's file.\n   - `lanes-repo-narrow` (done 2): on this repo, `lanes.py affected skills/workflow-health/scripts/judge.py` reruns\n     fewer than all land rows and only rows that belong to workflow-health (checked by the toy as: every rerun row\n     names a toy script whose starting set holds a workflow-health file).\n   - `lanes-always` (done 3): a row whose declaration cannot be resolved reruns on an unrelated change.\n   - `lanes-narrow-wide` (done 4): a narrow change reruns only its rows; a change to a file every row reaches reruns\n     all.\n   - `lanes-folder-var` (done 3, safety): an undeclared file used through a folder variable still reruns its row.\n","newText":"4. Rows in `.loop/regression.tsv` (goal REG-6, category criterion, descriptions as Given/When/Then), each seen\n   failing once with `regression.py red <id> --break` and passing:\n   - `lanes-headers` (done 1): every `dev/toy/*.sh` a row of this repo names has a `# reads:` header and declares\n     no skill `scripts/` folder (the CEO-accepted coverage check).\n   - `lanes-declared` (done 1): a declared script's rows rerun on a change to a declared file and not on a change to\n     another skill's file (ta/tb sets above).\n   - `lanes-folder-var` (done 1, narrowing safety): an undeclared file used through a folder variable set in another\n     file still reruns its row (solo.py → tm).\n   - `lanes-repo-narrow` (done 2): on this repo, `lanes.py affected skills/workflow-health/scripts/judge.py` reruns\n     fewer than half of the land rows, and every rerun row that is not an always row reaches judge.py through the\n     closure of a toy script whose `# reads:` header declares a file of `skills/workflow-health/` directly. Cross-skill\n     paths are computed, not grepped: the build runs `lanes.py affected` on judge.py once, and every rerun row that\n     is neither an always row nor a workflow-health row is listed as cross-skill in the PR table and excluded from\n     the check by id.\n   - `lanes-always` (done 3): a row whose declaration cannot be resolved reruns on a mapped change that does not touch it: tools/x.txt\n     → th, tx, tf, with tx and tf in the set and ta and tb not.\n   - `lanes-narrow-wide` (done 4): a narrow change reruns only its rows (solo.py set); a change to a file every row\n     reaches reruns all (dev/common.sh).\n"},{"oldText":"- \"Belongs to\" (for done 2's check) is defined from a row's starting set: the files its named toy scripts declare, name\n  literally, or match through the base-name rule.","newText":"- \"Belongs to\" (done 2): a non-always row belongs to a skill when a toy script it names declares a file of that skill\n  directly in its `# reads:` header. Item 4's `lanes-repo-narrow` uses exactly this definition."},{"oldText":"read from a file's first 40 lines. Several lines add up.","newText":"read from the whole file. Several lines add up."},{"oldText":"taken by base name: files with that base name in the same skill folder,\n       else anywhere under `skills/`, else in the file's own folder.","newText":"taken by base name: the union of every file with that base name in the same\n       skill folder, anywhere under `skills/`, and in the file's own folder."}]} -->

<!-- autoplan-accepted:ceo -->
- Header coverage check: a case in `dev/toy/test-lanes.sh` (regression part) reads `$here/.loop/regression.tsv`
  (the real repo root that test-lanes.sh resolves as `$here`), and for every `dev/toy/*.sh` a row names asserts it has
  at least one `# reads:` line and that no declared path is a skill `scripts/` folder (`skills/<s>/scripts/`). Its PASS
  line backs a new REG-6 row `lanes-headers` (done 1), seen failing once (a header removed) and passing, and rendered
  by item 5.
- `dev/toy/test-lanes.sh` gets its own header: `skills/workflow-regression/scripts/regression.py`,
  `skills/workflow-regression/scripts/lanes.py`, `skills/workflow-setup/scripts/setup.py`,
  `skills/workflow-delivery/scripts/goal.py`, `skills/workflow-delivery/scripts/flow.py`,
  `skills/workflow-delivery/scripts/role.py`.
- Read-trace completeness check (both CEO voices, finding "nothing checks that a declaration is complete"):
  `dev/toy/check-reads.sh [SCRIPT...]` runs each named toy script (default: every `dev/toy/*.sh` a land row names)
  once with `PYTHONPATH` pointing at a temporary `sitecustomize.py` whose `sys.addaudithook` logs every `open` and
  `cpython.run_file` path inside the repo's `skills/` tree to a trace file. It then asks
  `python3 lanes.py deps '<row command>'` for the union of the script's rows' closures and fails, naming the script
  and each file, when a traced skill file is outside that union. Coverage limit, stated in its header: Python reads
  only (bash `cat`/`grep` of skill files are covered by the static scan of the script text). `lanes.py deps COMMAND`
  prints the row's dependency set, one path per line, plus `ALWAYS: <reason>` when the row is always. A nightly row
  `lanes-trace` (REG-6, done 3) runs it, seen failing once (a declaration removed from one script) and passing; the
  build also runs it once over all 29 scripts before qa and fixes every header it flags.
- Fail-wide resolution rules (native CEO findings 5-6): quoted literal names in `.py` resolve to the union of every
  match (same skill folder, anywhere under `skills/`, own folder), never the first only; `# reads:` lines are read
  from the whole file, not the first 40 lines; a bare word `skills` used as a path after `cd "$here"` (as in
  `cp -R skills`) counts as the whole tree, like `$here/skills`; the base-name rule matches the file name with its
  extension (`board.py`), and a name built at run time must be declared.
- `lanes-headers` also fails when any header has a declaration problem (a missing or unresolvable path).
- A declared path whose normalized form leaves the repo root (absolute, or `..` escaping it) is a declaration
  problem (CEO section 3).
- Measurement (both voices): item 7's table adds (a) the floor: the rows that declare all of `skills/` and so rerun on
  every skill change, listed with their count; (b) `lanes.py affected` over the file lists of the last 15 merged
  goal PRs on main, before and after, as rows rerun and as row-seconds rerun (weighted by each row's seconds in the
  newest branch record under the git common dir's `loop/tests/`), with the median, and how many came out UNMAPPED.
<!-- /autoplan-accepted:ceo -->

### CEO phase, dual voices

Native CEO reviewer (completed, INPUT hash matched 41692ede): 9 findings, 3 high (tracing dismissed without
analysis; no completeness check on declarations; docs changes keep real PRs on full runs), 5 medium (whole-tree floor
of about 34 of 164 land rows; bare-tree detector depends on one spelling; first-match resolution and 40-line header
window; unproven helper premise and FULL runs without notes; six-month regret), 1 low (competitive).
Codex CEO voice (completed, gpt-6-astra via the model catalog): 6 findings, 1 critical (an incomplete but valid
declaration can silently skip a row when another row maps the file), 4 high (per-row process cost may be the real
cost: 164 rows collapse to 57 command prefixes; selection size is not time saved; the acceptance check lets the
implementation define its own correctness; no drift control), 1 medium (repo-specific rules exported as a template
capability). Recommendation: revise before implementation.

```
CEO DUAL VOICES — CONSENSUS TABLE:
  Dimension                            Claude  Codex  Consensus
  1. Premises valid?                    partly  partly CONFIRMED: "unknown deps always rerun" is not established
  2. Right problem to solve?            yes     maybe  DISAGREE: Codex names per-row process cost as a rival cause
  3. Scope calibration correct?         no      no     CONFIRMED: a completeness check is missing
  4. Alternatives sufficiently explored? no     no     CONFIRMED: tracing / batching dismissed without analysis
  5. Competitive/market risks covered?  low     medium DISAGREE (minor): template adopters
  6. 6-month trajectory sound?          no      no     CONFIRMED: header drift with no signal
```

Dispositions (auto-decided under the 6 principles; logged in the Decision Audit Trail):
- Completeness (both, critical/high): ACCEPTED in scope as the nightly read-trace check `lanes-trace` plus
  `lanes.py deps`. It does not change the user's direction (declarations stay the mechanism, as done line 1 says); it
  is the repair done line 3 ("never skipped") needs, so P1+P2 apply. Marked TASTE at the gate because it adds a
  nightly row of about one full suite's time.
- Tracing instead of headers (native 1): REJECTED as a replacement (done line 1 freezes declarations, and bash reads
  are invisible to a Python hook); used as the validator instead.
- Fail-wide resolution rules, `lanes-headers` problem check (native 5-7): ACCEPTED (mechanical safety).
- Measurement on historical diffs, duration-weighted, with the whole-tree floor (native 3-4, Codex 3): ACCEPTED.
- Per-row process cost / batching assertions per script run (Codex 2): DEFERRED. It needs `regression.py` changes the
  operation session kept out of this goal and overlaps regression-summary; filed as a finding at the end.
- Independent expected relationships (Codex 4): ADDRESSED by the trace check (observed reads are independent of the
  closure); cross-skill rows in `lanes-repo-narrow` stay computed, and the trace check backs them.
- Template adopters (Codex 6): no change. Narrowing is opt-in per script: a repo with no `# reads:` header keeps
  today's wide mapping byte-for-byte. Stated in the SKILL.md text.

### CEO review sections

Current scope: SELECTIVE EXPANSION. Accepted: header coverage check (proposal 1), read-trace check, fail-wide rules,
historical measurement. Deferred: header suggester, no-effect docs, batching. Skipped: per-row declarations, per-row
lane output. No UI scope.

1. Architecture. One module changes (lanes.py) plus data (headers) and tests. Dependency graph:
   ```
   regression.py run --reuse ──> lanes.plan() ──> closure(cmd)
                                                 ├─ no header named: wide path (today: references/widen/scan/walk)
                                                 └─ header named: narrow(seeds) ─> narrow_scan per file
                                                        ├─ .sh: exact files, non-skill folders, skill-folder marks
                                                        ├─ .py: imports + quoted names (union of matches)
                                                        └─ base-name fixpoint, why -> always
   lanes.py affected PATH... / deps CMD ──> same closure()   (read-only)
   check-reads.sh ──> toy script under sitecustomize audit hook ──> trace ⊆ deps ?
   ```
   Data paths: happy (declared row, narrow set); nil (no header: wide path unchanged); empty (header with no words:
   a declaration problem, always); error (unreadable file: `scan` already reads "" on OSError; narrow treats an
   unreadable seed as a declaration problem, always). Coupling: lanes.py gains no new import; check-reads depends on
   lanes.py's CLI only. Rollback: revert the commit; records invalidate by the runner hash, so the next run is full.
   No security surface (local files only). Value test: `lanes-trace` is consumed by the nightly run and fails loudly;
   `affected` is consumed by the PR table and by people asking why a row ran. Findings: 0 beyond the dual voices.
2. Error and rescue map: see the registry below. One GAP found and closed: an unreadable declared file must not narrow.
3. Security. No new inputs from outside the repo; `# reads:` paths are repo-relative and checked to exist; an absolute
   path or `..` escaping the repo is a declaration problem (added to the accepted rules by this section: a path whose
   normalized form leaves the repo root). `sitecustomize.py` lives in a private temp dir and is never committed.
   Likelihood low, impact low. 1 finding (path escape), mitigated.
4. Data flow and edge cases. `INPUT (# reads: words) -> VALIDATION (exists, no $*?, inside repo) -> TRANSFORM (narrow
   closure) -> PERSIST (none; cache per plan) -> OUTPUT (run/reuse ids, ALWAYS notes)`. Shadow paths: empty header
   (problem, always); duplicate words (set); CRLF line endings (strip); a header inside a heredoc in a toy repo the
   script writes (only lines starting with `#` at column 0 match; test-lanes writes its toy scripts with printf, not
   at column 0 of the outer file); a declared path that is a directory without trailing `/` (treated as a folder).
   No async or shared mutable state. 0 unhandled after these.
5. Code quality. New functions stay small; `closure()` branches once (header named or not). Risk of duplicating
   `references()`: `exact()` shares the regex and candidate logic through a flag, not a copy. 1 finding (share the
   candidate loop), accepted as an implementation note.
6. Tests. Diagram:
   ```
   NEW THING                         TEST                                   TYPE
   declared header parsing           test-lanes narrow section (ta/tb/tx)   integration (toy repo)
   narrow closure .sh/.py rules      exact rerun sets a.py/data.md/helper   integration
   folder variable across files      solo.py -> tm                          integration
   always reasons + notes            tx/tf + ALWAYS lines                   integration
   wide fallback unchanged           tu + every existing test-lanes check   regression
   header coverage on this repo      lanes-headers                          repo check
   completeness of headers           lanes-trace (nightly)                  system (all toy scripts)
   repo narrowing                    lanes-repo-narrow                      repo check
   affected/deps CLI                 toy AFFECTED-line comparison           integration
   ```
   2am-Friday test: `lanes-trace` over all scripts. Hostile QA: a script that builds a skill path at run time in
   Python (caught by the trace) or in bash with a loop (declared by hand; the trace catches the Python side).
   Flakiness: none (no time or network in the new checks). no_claim for lanes-trace: bash-only reads of skill files.
7. Performance. Narrow closure reads each reached file once per plan (cache); 29 scripts and about 60 skill files,
   well under a second. `check-reads.sh` costs about one full land suite (nightly only). 0 issues.
8. Observability. `ALWAYS <id>: <reason>` notes on reuse runs; `lanes.py affected/deps` for debugging; check-reads
   names the script and file on failure. Gap accepted from the native voice: FULL runs print no notes, so a broken
   header is caught by `lanes-headers` (land) instead. 1 gap, mitigated.
9. Deployment. No migration. First run after merge is FULL (runner hash changes). Rollback is a revert. Risk window:
   other open branches keep their old lanes.py until they merge main; their records stay valid for their own runner.
   0 risks beyond that.
10. Long-term trajectory. Debt: 29 headers to keep current, now checked nightly. Reversibility 5/5 (delete headers
    and the narrow branch). Path dependency: batching rows per script (deferred) can build on `deps`. A new engineer
    reads the rule in the regression SKILL.md and one header example.
11. Design: SKIPPED (no UI scope).

### CEO required outputs

NOT in scope:
- Deferred: `lanes.py declare` header suggester (P3); no-effect treatment for SKILL.md/references (needs its own
  goal and measurement); batching a script's rows into one execution (touches regression.py; overlaps
  regression-summary). Filed with `goal.py finding` at the end of the goal.
- Rejected: per-row declarations (upkeep 5x); per-row lane output on every run (noise); tracing as a replacement for
  headers (bash reads invisible; done line 1 freezes declarations).

What already exists: `references()`/`scan()`/`walk()`/`closure()` (wide mapping, reused as the fallback); `plan()`
(per-path decision, factored into a helper for `affected`); `NO_EFFECT`/`named()` (release files); the
regression.tsv and known-list rules; `regression.py red --break` (seen-red proof); `criteria.py render` (PRD Tests).

Dream state delta: after this plan, declared rows narrow and are checked nightly; docs changes and per-row process
cost remain the two things between this and the 12-month ideal.

Error & Rescue Registry:
```
  CODEPATH                 | WHAT CAN GO WRONG                  | RESCUE                         | USER SEES
  -------------------------|------------------------------------|--------------------------------|-----------------
  declared()               | missing / glob / outside-repo path | why -> always                  | ALWAYS note
  narrow_scan()            | unreadable file (OSError)          | seed: why -> always; else ""   | ALWAYS note
  narrow() base-name rule  | name built at run time             | declared by hand; lanes-trace  | nightly FAIL
  closure() mixed command  | undeclared named file              | its wide closure is added      | (wider set)
  affected CLI             | no .loop/regression.tsv            | exit 1 "NO ROWS"               | message
  check-reads.sh           | toy script fails                   | reported, check continues      | FAIL line
  check-reads.sh           | trace file missing (hook not run)  | FAIL "no trace for <script>"   | FAIL line
```
Failure Modes Registry:
```
  CODEPATH        | FAILURE MODE                         | RESCUED? | TEST?            | USER SEES?   | LOGGED?
  ----------------|--------------------------------------|----------|------------------|--------------|--------
  header drift    | valid but incomplete declaration     | Y        | lanes-trace      | nightly FAIL | Y
  bash-only read  | script cats a skill file by var name | partial  | static scan only | silent       | N
  broken header   | path missing                         | Y        | lanes-always     | ALWAYS note  | Y
  whole tree      | cp -R skills without $here           | Y        | narrow section   | always       | Y
```
The bash-only row is RESCUED partial, TEST static, USER SEES silent: not a CRITICAL GAP (the static scan covers
literal and folder-variable names; only a bash path built entirely at run time escapes, and the hand check covers
today's cases), recorded as a known limit.

```
  +====================================================================+
  |            MEGA PLAN REVIEW — COMPLETION SUMMARY                   |
  +====================================================================+
  | Mode selected        | SELECTIVE EXPANSION                         |
  | System Audit         | lanes widens every skill path; 164/164 rows |
  | Step 0               | Approach A kept; 1 expansion accepted       |
  | Section 1  (Arch)    | 0 issues found (beyond dual voices)         |
  | Section 2  (Errors)  | 7 error paths mapped, 1 GAP (closed)        |
  | Section 3  (Security)| 1 issue found, 0 High severity              |
  | Section 4  (Data/UX) | 5 edge cases mapped, 0 unhandled            |
  | Section 5  (Quality) | 1 issue found                               |
  | Section 6  (Tests)   | Diagram produced, 0 gaps                    |
  | Section 7  (Perf)    | 0 issues found                              |
  | Section 8  (Observ)  | 1 gap found (mitigated)                     |
  | Section 9  (Deploy)  | 0 risks flagged                             |
  | Section 10 (Future)  | Reversibility: 5/5, debt items: 1           |
  | Section 11 (Design)  | SKIPPED (no UI scope)                       |
  +--------------------------------------------------------------------+
  | NOT in scope         | written (6 items)                           |
  | What already exists  | written                                     |
  | Dream state delta    | written                                     |
  | Error/rescue registry| 7 rows, 0 CRITICAL GAPS                     |
  | Failure modes        | 4 total, 0 CRITICAL GAPS                    |
  | TODOS.md updates     | 3 items proposed (as findings; no TODOS.md) |
  | Scope proposals      | 5 proposed, 1 accepted                      |
  | CEO plan             | written                                     |
  | Outside voice        | codex completed (6 findings)                |
  | Lake Score           | N/A                                         |
  | Diagrams produced    | 2 (architecture, test map)                  |
  | Stale diagrams found | 0                                           |
  | Unresolved decisions | 0                                           |
  | Reality rows         | 7/7 rows, 0 unverified                      |
  +====================================================================+
```

REALITY: premise-table pass every factual claim has a receipt (164 land rows, 29 scripts, lanes.py 10,583 bytes, widen() at skills/workflow-regression/scripts/lanes.py:113) skills/workflow-regression/scripts/lanes.py:113
REALITY: already-done pass git log origin/main since 2026-11-08 on lanes.py/test-lanes.sh shows only test-lanes commits; no `# reads:` work exists skills/workflow-regression/scripts/lanes.py:158
REALITY: surface-check pass `regression.py run --reuse`, `red --break` and `criteria.py render` exist; `lanes.py affected/deps` are new commands this plan adds skills/workflow-regression/scripts/regression.py:418
REALITY: binding-decisions pass the decision search found no branch decisions; the operation session's scope limit (lanes.py row mapping and declarations) is honoured .loop/goals/narrow-rows.md:1
REALITY: numbers pass 164 land rows [measured: .loop/regression.tsv]; 1,441-1,589 row-seconds per full lane [measured: loop/tests records]; 34 whole-tree rows [estimated by the native reviewer, re-measure before gate] .loop/regression.tsv:1
REALITY: deferred-asks pass no linked issue; the held line's five done lines are all mapped .loop/goals/narrow-rows.md:9
REALITY: pr-count pass one PR (no ship-policy.json; default one PR per wave) .loop/goals/narrow-rows.md:1

### Decision Audit Trail

<!-- AUTONOMOUS DECISION LOG -->
| # | Phase | Decision | Classification | Principle | Rationale | Rejected |
|---|-------|----------|----------------|-----------|-----------|----------|
| 1 | CEO | Mode SELECTIVE EXPANSION | Mechanical | override | autoplan rule | other modes |
| 2 | CEO | Accept header coverage check | Mechanical | P1, P2 | in blast radius, < 1 day | defer |
| 3 | CEO | Defer header suggester | Mechanical | P3 | not needed for done lines | add |
| 4 | CEO | Defer no-effect docs | Taste | P3 | changes UNMAPPED safety; own goal | add now |
| 5 | CEO | Skip per-row declarations | Mechanical | P5 | 5x upkeep | add |
| 6 | CEO | Skip per-row lane output | Mechanical | P5 | `affected` covers it | add |
| 7 | CEO | Apply 0H spec findings (3 rounds) | Mechanical | P1 | clarity and exact sets | leave |
| 8 | CEO | Approve 0H documents | Mechanical | recommended | documents only | revise |
| 9 | CEO | Accept read-trace check (nightly) | Taste | P1, P2 | done line 3 needs completeness evidence | no check |
| 10 | CEO | Tracing as validator, not replacement | Mechanical | P5 | done line 1 freezes headers | replace |
| 11 | CEO | Fail-wide resolution rules | Mechanical | P1 | safety | first match |
| 12 | CEO | Historical, duration-weighted measurement | Mechanical | P1 | value, not size | single files only |
| 13 | CEO | Defer batching rows per script | Taste | P3 | regression.py out of scope | do now |
| 14 | CEO | Path escape is a declaration problem | Mechanical | P1 | security section | allow |
| 15 | CEO | Align item 1 text with the fail-wide rules (whole-file headers, union of matches) | Mechanical | P5 | close verification found the contradiction | leave both |
| 16 | DX | Mode DX POLISH, persona contributor agent, target Competitive | Mechanical | overrides | enhancement to an existing tool | EXPANSION/TRIAGE |
| 17 | DX | `lanes.py check` as the one header check, reporting every problem | Mechanical | P5 | both voices | first reason only |
| 18 | DX | CLI contract for affected/deps (root, levels, exits, channels) | Mechanical | P1 | both voices | leave unstated |
| 19 | DX | Reason codes, file:line, fix lines | Mechanical | P1 | agent-ready contract | message only |
| 20 | DX | check-reads invocation contract, hook marker, copied-tree mapping | Mechanical | P1 | CAP4 | bare script runs |
| 21 | DX | Header required on test-*.sh entry points only; wrappers exempt | Mechanical | P5 | Codex | all named files |
| 22 | DX | `LANES_WIDE=1` escape hatch | Taste | P3 | native voice; tiny | none |
| 23 | DX | `--why` reach chain | Taste | P1 | both voices; small | none |
| 24 | DX | Skip `--json` and dev/toy/README.md | Taste | P5, P4 | stable lines suffice | add |
| 25 | DX | State replacements of CEO-block text (invocations, ALWAYS format, entry points only) | Mechanical | P5 | close verification | leave contradictions |
| 26 | Eng | Accept E1/E2/E3/E4/E6/E10/E11/E13 and Codex 1-6 | Mechanical | P1 | false skips must be closed | leave |
| 27 | Eng | Split CLI into lanes_cli.py | Mechanical | P5 | size budget | one file |
| 28 | Eng | lanes-repo-narrow: computed, no-missing + threshold, not a hand-kept set | Taste | P3 | rot vs self-validation | reviewed set |
| 29 | Eng | No hard runtime threshold; report row-seconds and planning time | Taste | P6 | done line 2 defines success | threshold |
| 30 | Eng | check-reads runs each row's exact command (deduped), not extracted invocations | Mechanical | P5 | removes the shell-grammar problem | parse up to first pipe |

### DX phase (DX POLISH)

Product type: CLI tool inside a Claude Code skill (lanes.py, check-reads.sh, toy scripts). Auto-decided under the
autoplan overrides (persona inferred from README and the loop docs; mode DX POLISH; target Competitive).

```
TARGET DEVELOPER PERSONA
========================
Who:       a contributor, usually a worker agent, adding or changing a dev/toy test script and its regression rows
Context:   in a goal's build step, after writing a new test; later, a worker reading a lane's AFFECTED/ALWAYS lines
Tolerance: one command to check a header, one to see which rows a file feeds; it cannot ask anyone
Expects:   a copy-paste header example, errors that name the file, line and the line to add
```

Empathy narrative: "I added `dev/toy/test-thing.sh` and two rows. The lane still reran everything and I couldn't
tell why. The plan says I need a `# reads:` header, but where's the syntax? Spaces or commas? I wrote one, ran the
suite, and nothing told me whether it was right: the ALWAYS note only shows on a reuse run, and my first run was
FULL. When `lanes-headers` failed it said a path doesn't exist, but not which script or what to write instead."
(Predicted from the plan text; no implementation exists yet.)

Competitive benchmark (DX choices, no timed peers): Bazel/Pants declare deps per target and fail the build on an
undeclared input (sandboxing); pytest-testmon infers deps from coverage at run time; Jest `--findRelatedTests`
infers from the import graph. This plan is a hybrid (declared entry points, inferred closure, traced validation).
Clock: from a new toy script with rows to `lanes.py affected <file>` showing its rows narrow, with a passing header
check. Today: no path exists (about 4 undocumented steps). Target: Competitive, 2-5 min, 3 steps.
Magical moment: `python3 lanes.py affected skills/<skill>/scripts/<file>.py` prints `AFFECTED 6 of 164 rows (...)`
on this repo, with a `--why` chain per row. Vehicle: the existing `affected` command (no new surface).

Developer journey:
```
STAGE           | DEVELOPER DOES                               | FRICTION                         | STATUS
----------------|----------------------------------------------|----------------------------------|-------
1. Discover     | reads regression SKILL.md                    | rule was "a few lines"           | fixed (grammar, example, table)
2. Install      | nothing to install                           | none                             | ok
3. Hello World  | writes header, runs `lanes.py check <script>`| no single check command          | fixed (lanes.py check)
4. Real Usage   | `lanes.py affected <file>` before committing | root/levels/exit codes unstated  | fixed (CLI contract)
5. Debug        | `lanes.py deps <cmd> --why <file>`           | no reach chain; ALWAYS hidden    | fixed (--why; check reports all)
6. Upgrade      | first run after merge is FULL                | expected full run unexplained    | fixed (docs: record invalidation)
```

First-time developer report: T+0:00 opens SKILL.md, finds the header grammar and one example. T+0:40 pastes a
header, runs `lanes.py check dev/toy/test-thing.sh`: one line per problem with code, file:line and the line to add.
T+1:30 fixes it, runs `lanes.py affected skills/x/scripts/y.py`: sees its two rows. T+2:30 done; nightly
`lanes-trace` later confirms nothing was missed.

Dual voices: native DX reviewer (completed, INPUT dx 6b970af0 matched): 1 critical (CAP4 check-reads can pass
having seen nothing), 6 high CAP6 (no file/line/fix in reasons, wrong reason class, check-reads gives no fix, cleanup
unstated, usage errors unspecified, raw tracebacks), and medium/low items (codes, notes invisible on FULL runs,
UNMAPPED hint, docs depth, LANES_WIDE escape hatch, `# reads: skills/` as documented opt-out, format consistency).
Codex DX voice (completed): 4 high (check-reads cannot run scripts bare: rows pass arguments and wrappers, and copied
trees escape the filter; header coverage contradicts the ci-env.sh exemption; under-five-minute target unsupported,
`add` defaults to nightly; diagnostics vanish on FULL runs), 4 medium (agent-ready output contract; `affected` is not
an exact execution preview; docs entry point; migration behavior).

```
DX DUAL VOICES — CONSENSUS TABLE:
  Dimension                           Claude  Codex  Consensus
  1. Getting started < 5 min?          no      no     CONFIRMED: needs a check command and a walkthrough
  2. API/CLI naming guessable?         partly  partly CONFIRMED: root, levels, exit codes, format unstated
  3. Error messages actionable?        no      no     CONFIRMED: file, line, fix and codes missing
  4. Docs findable & complete?         no      no     CONFIRMED: "a few lines" is not enough
  5. Upgrade path safe?                partly  partly CONFIRMED: needs an escape hatch and migration notes
  6. Dev environment friction-free?    no      no     CONFIRMED: check-reads invocation contract missing
```

Passes (before → after the accepted fixes):
1. Getting started 3 → 7: `lanes.py check` plus the SKILL.md walkthrough; three steps.
2. API/CLI 5 → 8: CLI contract below; `--why`; one `ALWAYS <id>: <reason>` format everywhere.
3. Errors 4 (CAP4) → 7: check-reads fails on a missing hook marker or a failed script; reasons carry code, file:line
   and a fix line; usage errors exit 2 on stderr; unexpected errors print one line plus `LANES_DEBUG=1` for the trace.
   ```
   ERROR PATH MATRIX (agent-ready-v1)
   Path                     | Class      | what | fix | recovery | code | context | trace | redaction | channel
   declaration problem      | validation | pass | pass| pass     | pass | pass    | N/A   | pass      | pass (always row; check exits 1)
   affected: no table       | usage      | pass | pass| N/A      | pass | N/A     | N/A   | pass      | pass (stderr, exit 2)
   check-reads: no marker   | dependency | pass | pass| pass     | pass | pass    | pass  | pass      | pass (exit 1)
   unexpected exception     | crash      | pass | pass| pass     | pass | pass    | pass  | pass      | pass (exit 1)
   ```
   Redaction: only repo-relative paths are printed; no environment or command text goes into traces.
4. Documentation 2 → 7: grammar, example, reason→fix table, closure rules, opt-out, walkthrough, migration note.
5. Upgrade 6 → 8: headerless scripts unchanged (compatibility promise stated); first post-merge run FULL is documented;
   `LANES_WIDE=1` returns any run to the wide mapping.
6. Dev environment 4 → 7: check-reads invocation contract (per distinct row invocation, wrappers kept, copied trees
   mapped back, temp dir cleaned by trap).
7. Community 7 → 7: MIT, public; no change in scope. No issues.
8. DX measurement 5 → 7: the PR table (historical diffs, row-seconds) and nightly `lanes-trace` are the feedback
   loop; no telemetry added.

```
+====================================================================+
|              DX PLAN REVIEW — SCORECARD                             |
+====================================================================+
| Dimension            | Score  | Prior  | Trend  |
|----------------------|--------|--------|--------|
| Getting Started      | 7/10   | 3/10   | +4     |
| API/CLI/SDK          | 8/10   | 5/10   | +3     |
| Error Messages       | 7/10   | 4/10   | +3     |
| Documentation        | 7/10   | 2/10   | +5     |
| Upgrade Path         | 8/10   | 6/10   | +2     |
| Dev Environment      | 7/10   | 4/10   | +3     |
| Community            | 7/10   | 7/10   | 0      |
| DX Measurement       | 7/10   | 5/10   | +2     |
+--------------------------------------------------------------------+
| TTHW                 | ~3 min | none   | new    |
| Competitive Rank     | Competitive                                  |
| Magical Moment       | designed via `lanes.py affected --why`       |
| Product Type         | CLI tool in a Claude Code skill              |
| Mode                 | POLISH                                       |
| Overall DX           | 7/10   | 4/10   | +3     |
+====================================================================+
```

DX implementation checklist: header grammar + example in SKILL.md; `lanes.py check` as the one pre-commit command;
`affected` and `deps` CLI contract (root, levels, exit codes, stdout/stderr, ordering); reason codes with fix lines;
check-reads invocation contract and hook marker; `LANES_WIDE=1`; `# reads: skills/` documented as the opt-out;
walkthrough with explicit `--level land`; migration note (first run FULL).

NOT in scope (DX): a `--json` output mode (stable line formats suffice for the PR table and tests; P5); a
`dev/toy/README.md` entry point (the regression SKILL.md is where the loop's docs live; P4); timing a fresh
contributor (no such person available in an unattended run).


<!-- autoplan-accepted:dx -->
- Header grammar: a line `# reads: <path> [<path>...]` at column 0, anywhere in the file; paths are repo-relative,
  separated by whitespace, unquoted; a trailing `/` marks a folder; nothing else on the line. `# reads: skills/` is
  the documented per-script opt-out (stay wide). Headers are required on every `dev/toy/test-*.sh` that a row names;
  wrappers such as `ci-env.sh`, `make.sh` and `fakegh/` are exempt and followed.
- `python3 lanes.py check [SCRIPT...]` (default: every `dev/toy/test-*.sh` a row of this repo names) validates
  headers statically and runs the narrow closure per script, reporting every problem, not the first only, as
  `<CODE> <script>:<line>: <what>` with a last line `fix: <the line to add or change>`. Codes:
  `LANES-DECL-MISSING` (path does not exist), `LANES-DECL-PATTERN` (`$`, `*`, `?` in a path), `LANES-DECL-ESCAPE`
  (absolute or leaves the repo), `LANES-DECL-FOLDER` (names a skill folder, declares no file in it),
  `LANES-DECL-TREE` (names all of skills/ without declaring `skills/`), `LANES-DECL-NONE` (a test script with no
  header). Exit 0 clean, 1 problems, 2 usage. `lanes-headers` runs `lanes.py check` on this repo.
- CLI contract for `affected`, `deps` and `check`: the repo root is `git rev-parse --show-toplevel` of the current
  directory, overridden by `--root DIR`; PATH arguments are normalized to repo-relative and a path outside the repo
  is a usage error; `--level land|nightly|all` (default `land`, matching `regression.py run land`); results on
  stdout, sorted, one fixed-prefix line each (`AFFECTED n of m rows (id, id, ...)`, `UNMAPPED <path>: full run;
  no row reads it (add it to a script's # reads: if one should)`, `ALWAYS <id>: <reason>`); usage errors on stderr
  with exit 2 (no table under the root, unknown level, no PATH, unknown subcommand); unexpected errors print one
  line naming the file and row and exit 1, with the full trace only under `LANES_DEBUG=1`. `deps COMMAND` prints
  dependency paths sorted, then `ALWAYS <command>: <reason>` lines; `deps COMMAND --why PATH` prints the reach chain
  from the command to PATH (`dev/toy/t.sh -> skills/a/scripts/a.py -> skills/a/scripts/data.md`), or `NOT REACHED`.
  `affected` is documented as dependency impact, not an exact preview: it has no record, so FAIL rows, ancestry and
  edited rows are outside it.
- `check-reads.sh` invocation contract: it groups the rows of the selected scripts by their invocation (the command
  up to the first `|`, wrappers and arguments kept, e.g. `bash dev/toy/ci-env.sh bash dev/toy/test-docs.sh`) and runs
  each distinct invocation once from the repo root, in a `mktemp -d` dir removed by a trap; the sitecustomize hook
  writes a start marker per Python process; a traced path containing `/skills/<s>/<rest>` under any directory is
  mapped back to `skills/<s>/<rest>` when that repo file exists (copied trees); it fails when an invocation exits
  non-zero (exit code and the last 5 stderr lines), when an invocation that runs Python left no marker
  (`LANES-TRACE-NOHOOK: PYTHONPATH reset or -I/-S?`), or when a traced skill file is outside the union of those rows'
  closures (`LANES-TRACE-UNDECLARED <script> <file>` plus `fix: # reads: <file>`). Python reads only, stated.
- `LANES_WIDE=1` in the environment makes `closure()` take the wide path for every row (documented as the first step
  when a narrowed lane is suspected of missing a row).
- Docs (regression SKILL.md and references/commands.md, under their own new headings): the grammar with a
  copy-paste example, the closure rules in five lines, a reason→fix table with the codes, `affected`/`deps`/`check`
  usage with sample output, the opt-out, `LANES_WIDE=1`, the coverage limit of check-reads, a three-step walkthrough
  for a new test script (write the header, `lanes.py check <script>`, `lanes.py affected <file>`; register rows with
  `regression.py add ... --level land`), and the migration note (headerless scripts keep the wide mapping; the first
  run after lanes.py changes is FULL because records carry the runner hash).
- Replacements of earlier text (this block wins where they differ): `check-reads.sh` runs each distinct row
  invocation once, not each script bare; `deps` prints `ALWAYS <command>: <reason>`, not `ALWAYS: <reason>`; the
  header coverage check (`lanes-headers`, item 4 and the CEO block) applies to `dev/toy/test-*.sh` entry points a row
  names, not to wrappers such as `ci-env.sh`; `lanes-headers` asserts `lanes.py check` exits 0 on this repo.
<!-- /autoplan-accepted:dx -->

### Eng phase

Scope Challenge: the selected work touches lanes.py, a new lanes_cli.py, a new check-reads.sh, 29 toy script headers,
test-lanes.sh, regression.tsv, the PRD page and two docs (about 36 files, mostly one-line headers; 2 new modules).
The complexity gate trips on file count, but the headers are data, not code; the code change is three files.
Structure (auto-decided, recommended): original arrangement plus the lanes_cli.py split (E9). Scope accepted as-is.

Native Eng reviewer (completed, INPUT eng d0bac06d matched): 13 findings (E1-E13): 2 high (`"$here"/skills/...`
split quoting and globs are invisible to the narrow scan, verified at test-board.sh:232, test-health-judge.sh:116,
test-rows.sh:63, test-health.sh:104, test-adopt.sh:54; the scripts/-folder ban conflicts with real globs), 7 medium
(ROOT/whole semantics; directory listings untraced; extension-less quoted folders; plan() parity guard;
lanes-repo-narrow brittleness; size budget), 4 low (heredoc headers, loose base-name match, leftover wording, security
hygiene).
Codex Eng voice (completed): 8 findings: 5 high (deleted transitive files vanish while a broad row hides UNMAPPED;
glob dependencies and split quoting, confirmed by running the regex; one hook marker masks an unhooked child;
copied-tree mapping misses renamed and flat copies used by test-docs-command.sh:40; the narrow branch drops
command-level directories), 3 medium (`up to the first |` breaks on `out=$(...)` rows such as prd-section-order;
lanes-repo-narrow is self-validating; measurement baseline and runtime criterion).

```
ENG DUAL VOICES — CONSENSUS TABLE:
  Dimension                           Claude  Codex  Consensus
  1. Architecture sound?               no      no     CONFIRMED: quoting/glob gap; folder rule; dropped dirs
  2. Test coverage sufficient?         no      no     CONFIRMED: repo-narrow check brittle/self-validating
  3. Perf risks + budget/bench named?  partly  no     CONFIRMED: size budget; runtime measurement gaps
  4. Security threats covered?         yes     n/a    DISAGREE (minor): only native covered hygiene
  5. Error paths handled?              no      no     CONFIRMED: trace can pass incomplete (hook, copies)
  6. Deployment risk manageable?       yes     yes    CONFIRMED: first run FULL, revertable
```

Section 1, Architecture:
```
 regression.py run --reuse ─> lanes.plan(): deletions under skills/ or dev/ ─> FULL
                                │
                                └─> closure(cmd) ──LANES_WIDE=1 or no header named──> wide (unchanged)
                                        │ header named
                                        ├─ command-level files, dirs, bare-tree, ROOT kept (Codex 5)
                                        └─ narrow(seeds)
                                             ├─ header: leading comment block only (else LANES-DECL-PLACE)
                                             ├─ .sh: exact() incl. "$here"/ ${here}/ forms; globs -> static prefix folder
                                             ├─ .py: imports, quoted names (union), quoted existing folders
                                             └─ base-name rule: word-bounded, recursive in recorded folders
 lanes_cli.py (affected | deps [--why] | check) ─imports─> lanes
 check-reads.sh ─> per row command (deduped), process group, timeout
        ├─ PYTHONPATH=<tmp>:$PYTHONPATH sitecustomize: open, run_file, listdir, scandir, glob events
        ├─ PATH shim python3: logs every launch; launches vs markers -> LANES-TRACE-NOHOOK
        └─ outside-repo reads mapped by content hash to repo skill files
```
Design-twice: shape A (chosen) keeps one closure() with a narrow branch; shape B would give each row a stored
dependency manifest generated from traces (`.loop/regression-deps.tsv`), checked in CI. B hides more behind a smaller
interface but adds a hand-synced list (red flag 8) unless regenerated nightly; A keeps one owner of the mapping
(lanes.py) and uses traces only to validate. Red flags in A: `exact()` vs `references()` risk two ways to scan
(flag 6) — fixed by one scanner with a `widen` flag; lanes_cli.py must not re-implement decisions (flag 4) — it only
calls `closure()`, `affected()` and `check()`.
Findings: E1, E2, E3, E5(cmd dirs), Codex 1, 2, 5 — all accepted (below). Realistic production failure: a toy script
adds `for f in "$here"/skills/x/scripts/*.py` and the row silently stops rerunning — closed by E1+E2.

Section 2, Code quality: [INFORMATIONAL] (confidence 8/10) lanes.py:118 `references()` — `exact()` must share it via a
flag rather than copy it. [INFORMATIONAL] (8/10) lanes.py:200 `plan()` — the per-path decision moves to one helper
used by `affected()` (parity guard E7). [INFORMATIONAL] (7/10) E9 size: split CLI into lanes_cli.py.
Dispositions: accepted.

Section 3, Tests: test plan artifact written to the private review folder
(the eng review test plan for this branch). Coverage diagram:
```
CODE PATHS                                         USER FLOWS
[+] lanes.closure()                                [+] contributor adds a test script
  ├── [★★★ PLANNED] wide (tu, LANES_WIDE oracle)     ├── [★★★ PLANNED] lanes.py check -> fix line
  ├── [★★★ PLANNED] narrow .sh/.py/base-name sets    └── [★★  PLANNED] affected shows its rows
  ├── [★★★ PLANNED] split quoting + globs (E1)     [+] worker reads a lane
  ├── [★★★ PLANNED] backed folder decl (E2)          └── [★★  PLANNED] ALWAYS/UNMAPPED lines
  ├── [★★★ PLANNED] command dirs kept (Codex 5)
  └── [★★★ PLANNED] header placement (E10)
[+] lanes.plan()
  ├── [★★★ EXISTING] all current test-lanes checks (unchanged)
  └── [★★★ PLANNED] deletion -> FULL with broad row present (Codex 1)
[+] check-reads.sh
  ├── [★★★ PLANNED] undeclared Python read fails
  ├── [★★★ PLANNED] unhooked child after hooked setup fails (Codex 3)
  └── [★★★ PLANNED] renamed/flat copy maps by hash (Codex 4)
COVERAGE: 14/14 planned paths have a planned ★★+ test | GAPS: 0
```
Regression rule: the existing test-lanes regression and delivery parts must pass unchanged (behavior at risk: the
wide mapping and plan()); the LANES_WIDE parity oracle backs it.

Section 4, Performance: narrow closure is per plan, cached, about 29 scripts and 60 skill files: well under a second
(bench: `time python3 lanes.py affected <file>` reported in the PR). check-reads costs one land suite of row time
(about 1,450-1,590 s) and runs nightly with a per-row timeout of 600 s. No unbounded loops: the base-name fixpoint
adds only existing files, so it terminates.

Failure modes (new paths): split-quoted glob read (closed by E1, test); new file in a globbed folder (E2, test);
deleted helper (Codex 1, FULL, test); unhooked child (Codex 3, shim, test); copied script (Codex 4, hash, test);
bash read by computed name (no test; static scan covers literal forms; stated limit; not silent for Python). No
critical gap: every silent path has a test or is a stated, bounded limit.

NOT in scope (Eng): a stored per-row dependency manifest (shape B); a hard runtime threshold for the PR measurement
(taste: done line 2 defines success; the PR reports row-seconds and planning time instead); batching rows per script
(deferred by CEO); a reviewed hand-kept expected set for lanes-repo-narrow (rots as rows are added; taste).
What already exists: references/scan/walk/closure/plan/hits/named in lanes.py; regression.py's per-row runner and
`red --break`; criteria.py render; the 600 s row timeout convention in regression.py.
Parallelization: sequential implementation, no parallelization opportunity (one primary module).
TODOS.md: this repo keeps none; the deferred items (header suggester, no-effect docs, batching rows per script)
are filed with `goal.py finding` at the end of the goal.

Completion summary: Step 0 scope accepted as-is; reality rows 7/7; Architecture 7 issues; Code quality 3; Tests:
diagram produced, 0 gaps after accepted additions; Performance 0; failure modes 0 critical gaps; unresolved 0;
outside voice codex completed (8 findings); parallelization 1 lane sequential; Lake Score N/A.

REALITY: premise-table pass the split-quote gap and glob reads are verified at dev/toy/test-board.sh:232 and dev/toy/test-health-judge.sh:116 dev/toy/test-health-judge.sh:116
REALITY: already-done pass no narrowing work on origin/main since 2026-11-08 skills/workflow-regression/scripts/lanes.py:113
REALITY: surface-check pass `lanes.py` has no CLI today (import-only docstring), so affected/deps/check are new; `regression.py red --break` exists skills/workflow-regression/scripts/lanes.py:4
REALITY: binding-decisions pass operation session: edits limited to lanes.py row mapping and declarations; lanes_cli.py and check-reads.sh serve that mapping .loop/goals/narrow-rows.md:1
REALITY: numbers pass 164 land rows, 29 named test scripts, lanes.py 10,583 bytes [measured: .loop/regression.tsv, wc] .loop/regression.tsv:1
REALITY: deferred-asks pass no linked issue; all five done lines mapped .loop/goals/narrow-rows.md:9
REALITY: pr-count pass one PR .loop/goals/narrow-rows.md:1


<!-- autoplan-accepted:eng -->
- Scanner (E1): `exact()` and the bare-tree test accept `$here/`, `${here}/`, `"$here"/` and `"${here}"/` path
  forms; a path in script text containing `*` or `?` counts as its static prefix folder (the part before the first
  glob character, cut back to a `/`): a skill folder becomes a recorded skill-folder mention, `skills/` a bare-tree
  mention, anything else a prefix dependency. `exact()` and `references()` share one implementation with a `widen`
  flag.
- Backed folder declarations (E2): declaring a skill folder (`skills/<s>/scripts/` or `skills/<s>/`) is allowed when
  the declaring script's text globs or recursively reads that folder; otherwise `lanes.py check` reports
  `LANES-DECL-FOLDER-UNBACKED` and the row is always. The header coverage rule bans only unbacked folder
  declarations. Size-loop files are covered by the backed folder, not listed by hand.
- Narrow-branch semantics (E3, Codex 5): the command's own files, directories, bare-tree flag and ROOT are kept as
  today before narrowing; a reached file's `cd "$here"` or bare `$here` adds nothing (as today), and its whole-tree
  forms are caught by the scanner rule above.
- Python follow (E6): a quoted literal in a reached `.py` that resolves to an existing folder in the same skill is a
  folder dependency (walked).
- Header placement (E10, replaces "read from the whole file"): `# reads:` lines are read from the leading comment block
  (after an optional shebang, consecutive lines starting with `#`); a `# reads:` line at column 0 anywhere else is
  `LANES-DECL-PLACE` and the row is always.
- Base-name rule (E11): word-bounded match of the file name with extension; files are matched recursively under each
  recorded skill folder.
- Deletions (Codex 1): in `plan()`, a deleted or renamed path under `skills/` or `dev/` since the recorded commit
  (`git diff --name-status`) forces FULL (`FULL: deleted <path>`); `affected` prints `DELETED <path>: full run`.
  Test: delete a helper imported by one row while another row declares `skills/`.
- check-reads.sh (Codex 3, 4, 6, E4, E13, replaces the invocation-grouping rule): it runs each row's exact command
  (identical commands once) from the repo root in its own process group with a 600 s timeout (descendants killed),
  with `PYTHONPATH=<tmp>:$PYTHONPATH`, a `python3`/`python` shim first on PATH that logs every launch and execs the
  real interpreter, and a sitecustomize audit hook logging `open`, `cpython.run_file`, `os.listdir`, `os.scandir` and
  `glob.glob`; it fails per row on a non-zero exit, on launches without a matching hook marker
  (`LANES-TRACE-NOHOOK`), or on a traced skill file or listed skill folder outside that row's closure
  (`LANES-TRACE-UNDECLARED`); reads outside the repo are mapped to repo skill files by content hash (renamed and flat
  copies); realpath is used for every path. Fixtures: a hooked setup process plus an unhooked `python3 -I` child, and a
  renamed and a flat copy.
- Parity guard (E7): a test-lanes case runs `lanes.py affected` with and without `LANES_WIDE=1` on a toy repo with no
  headers and requires identical output; every existing test-lanes check passes unchanged.
- lanes-repo-narrow (E8, Codex 7, replaces the exclusion-by-id rule): reruns fewer than half the land rows, includes
  every row whose named test script declares a `skills/workflow-health/` file (no missing rows), and prints each
  other non-always row with its `deps --why` chain for the PR table.
- CLI module (E9): `affected`, `deps` and `check` live in `skills/workflow-regression/scripts/lanes_cli.py`, which
  imports lanes; lanes.py keeps the mapping and stays under 20 KB.
- Measurement (Codex 8): the before column comes from a pinned copy of main's lanes.py at the merge base run through
  the same harness; the row population is the PR branch's table; rows without a recorded duration are counted and
  reported as unknown, never zero; the PR also reports `affected` wall time.
<!-- /autoplan-accepted:eng -->

### Final gate (Phase 4)

URGENT, outside this plan: None.
The run stopped at its final gate (gate_rev 1, rec_hash 12d0ddc2af1a), which this worker step never approves:
d1 nightly read-trace check (recommended: build it), d2 defer batching rows per script, d3 defer no-effect docs,
d4 include LANES_WIDE and `--why`, d5 computed lanes-repo-narrow, d6 no hard runtime threshold, p1 plan approval
(pending). The build follows the recommendations unless the owner replies otherwise.
Cycle: 29 min (CEO 13, DX 6, Eng 10). Coverage: CEO, DX and Eng each had a completed native reviewer and a completed
Codex outside voice (gpt-6-astra); design skipped (no UI scope).

## REVIEW REPORT

| Review | Trigger | Why | Runs | Status | Findings |
|--------|---------|-----|------|--------|----------|
| CEO Review | `/plan-ceo-review` (via /autoplan) | Scope & strategy | 1 | ISSUES OPEN (not logged: gate unapproved) | 5 proposals, 1 accepted, 2 deferred; 4 more accepted from dual voices |
| Outside Review | codex (gpt-6-astra), CEO/DX/Eng | Independent 2nd opinion | 3 | completed | 22 findings; all resolved or recorded as taste decisions |
| Eng Review | `/plan-eng-review` (via /autoplan) | Architecture & tests (required) | 1 | ISSUES OPEN (not logged: gate unapproved) | 10 issues, 0 critical gaps |
| Design Review | `/plan-design-review` | UI/UX gaps | 0 | skipped (no UI scope) | — |
| DX Review | `/plan-devex-review` (via /autoplan) | Developer experience gaps | 1 | ISSUES OPEN (not logged: gate unapproved) | score 4/10 → 7/10, TTHW none → ~3 min |

- **OUTSIDE COVERAGE:** codex completed in CEO (6 findings), DX (8) and Eng (8); design phase skipped.
- **CROSS-MODEL:** CEO 4/6 confirmed (disagreements: rival cost cause, template adopters); DX 6/6; Eng 5/6 (security covered by native only).
- **VERDICT:** no review CLEAR until the owner answers the gate; eng review required.

**UNRESOLVED DECISIONS:**
- p1: plan approval (owner gate, gate_rev 1)
