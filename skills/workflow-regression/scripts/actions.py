#!/usr/bin/env python3
"""The Actions workflow regression.py writes: runs the rows on a schedule, one issue per failing row."""
import json
import os
import re
import sys

# No terminal, no waiting: a prompt from git or gh must fail, not block.
os.environ.update(GIT_TERMINAL_PROMPT="0", GH_PROMPT_DISABLED="1", GIT_EDITOR="true", GIT_ASKPASS="true", SSH_ASKPASS="true")
if not sys.stdin or not sys.stdin.isatty():
    os.dup2(os.open(os.devnull, os.O_RDONLY), 0)

BUDGET_MINUTES = 30  # a scheduled regression job's budget (REG-7, AUT-7)
SHARDS = 2


ROW_DROP = ("GH_TOKEN", "GITHUB_TOKEN", "GITHUB_STEP_SUMMARY", "GITHUB_ENV", "GITHUB_OUTPUT", "GITHUB_PATH", "GITHUB_STATE",
            "REGRESSION_RESULTS", "REGRESSION_MAP", "RUNNER_TEMP", "SUITE_TIME_FILE")


def row_env():
    """A row's environment: no GitHub token and no runner file a row could write into."""
    return {k: v for k, v in os.environ.items() if k not in ROW_DROP}


WORKFLOW = r"""# Written by workflow-regression. It reads .loop/regression.tsv and .loop/regression-known.tsv.
name: regression
on:
@SCHEDULE@  push:
    tags: ["v*"]
  workflow_dispatch:
    inputs:
      target:
        description: "land, nightly or a row id; empty runs @LEVELS@ (the ci_levels setting)"
        required: false
        default: ""
        type: string
      cleanup:
        description: "true: run no row; close skipped-only and duplicate issues (paced)"
        required: false
        default: false
        type: boolean
permissions:
  contents: read
  issues: write
  pull-requests: read
concurrency:
  group: regression
  cancel-in-progress: false
jobs:
  regression:
    runs-on: ubuntu-latest
    timeout-minutes: @BUDGET@
    strategy:
      fail-fast: false
      matrix:
        shard: @MATRIX@
    steps:
      - uses: actions/checkout@v4
        with:
          persist-credentials: false
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - name: Check the routine
        id: routine
        env:
          EVENT: ${{ github.event_name }}
        run: |
          cron=$(python3 -c 'import json; print(json.load(open(".loop/config.json")).get("regression_cron") or "")' 2>/dev/null || true)
          if [ "$cron" = off ] && [ "$EVENT" = schedule ]; then
            echo "on=false" >> "$GITHUB_OUTPUT"
            echo "OFF: regression is off in .loop/config.json (regression_cron), so this run writes nothing." | tee -a "$GITHUB_STEP_SUMMARY"
            exit 0
          fi
          echo "on=true" >> "$GITHUB_OUTPUT"
          if [ -n "$cron" ] && [ "$cron" != "@CRON@" ]; then
            said="SCHEDULE: this workflow runs on '@CRON@' but .loop/config.json says '$cron'. Fix: python3 skills/workflow-regression/scripts/regression.py workflow"
            echo "::warning::$said"; echo "$said" >> "$GITHUB_STEP_SUMMARY"
          fi
      - name: Run the rows, and keep one issue per failing row
        if: steps.routine.outputs.on == 'true'
        env:
          GH_TOKEN: ${{ github.token }}
          REGRESSION_RESULTS: ${{ runner.temp }}/regression-results.tsv  # the runner's own file, in no row's environment
          SUITE_TIME_FILE: ${{ runner.temp }}/suite-time.tsv  # for health
          REGRESSION_TARGET: ${{ inputs.target }}  # by hand; checked below, never in a shell line
          REGRESSION_CLEANUP: ${{ inputs.cleanup }}
          REGRESSION_LEVELS: "@LEVELS@"  # the schedule and v* tags run ci_levels
          REGRESSION_SHARD: "${{ matrix.shard }}/@SHARDS@"  # this job runs one wanted row in @SHARDS@
        run: |
          here=$(mktemp -d)  # what each row guards, read before any row runs
          cat > "$here/tests.py" <<'TESTS_PY_EOF'
@TESTS@
          TESTS_PY_EOF
          python3 -I "$here/tests.py" list --tsv > "$here/map.tsv" 2>/dev/null || true
          export REGRESSION_MAP="$here/map.tsv"
          python3 - <<'PY'
          import json, os, re, subprocess, sys, tempfile, time, urllib.parse
          def rows(path):
              if not os.path.exists(path):
                  return []
              return [line.rstrip("\n").split("\t") for line in open(path) if line.strip() and not line.startswith("#")]
          known = {row[0] for row in rows(".loop/regression-known.tsv")}
          TARGET = os.environ.get("REGRESSION_TARGET") or os.environ.get("REGRESSION_LEVELS") or "nightly"
          if not re.fullmatch(r"land|nightly|[A-Za-z0-9_.-]+", TARGET) or TARGET not in ("land", "nightly") and \
                  TARGET not in [row[0] for row in rows(".loop/regression.tsv")]:
              print("REFUSED (BAD_TARGET): bad target %s: use land, nightly or a row id from regression.py list. Fix: rerun the "
                    "workflow with one of those" % json.dumps(TARGET), file=sys.stderr)
              sys.exit(1)
          def wanted(row):
              return row[0] == TARGET if TARGET not in ("land", "nightly") else row[1] in ("land", TARGET)
          def gh(*args, body=None):  # a text goes in a file, not the command line (Windows caps it)
              with tempfile.TemporaryDirectory() as tmp:
                  if body is not None:
                      open(tmp + "/b", "wb").write(body.encode())
                      args += ("--body-file", tmp + "/b")
                  return subprocess.run(("gh",) + args, capture_output=True, text=True)
          def seconds(name, default):
              try:
                  value = int(os.environ.get(name) or default)
              except ValueError:
                  return default
              return value if value > 0 else default
          ROW_SECONDS, JOB_SECONDS = seconds("REGRESSION_ROW_SECONDS", 900), seconds("REGRESSION_JOB_SECONDS", (@BUDGET@ - 2) * 60)
          ROW_ENV = {k: v for k, v in os.environ.items() if k not in @ROWDROP@}
          def run(command):  # own group, output to a file
              with tempfile.TemporaryFile("w+", errors="replace") as log:
                  child = subprocess.Popen(command, shell=True, stdout=log, stderr=subprocess.STDOUT, env=ROW_ENV,
                                           start_new_session=True)
                  timed_out = False
                  try:
                      child.wait(timeout=ROW_SECONDS)
                  except subprocess.TimeoutExpired:
                      timed_out = True
                      try:  # so a hang names itself
                          ps = subprocess.run(["ps", "-o", "pid,ppid,stat,wchan:20,args", "-s", str(child.pid)], capture_output=True, text=True)
                          log.write("\nprocesses at the timeout:\n" + ps.stdout)
                      except OSError:
                          pass
                  try:
                      os.killpg(child.pid, 9)
                  except OSError:
                      pass
                  except AttributeError:  # Windows: no process groups, taskkill takes the tree
                      subprocess.run(["taskkill", "/T", "/F", "/PID", str(child.pid)], capture_output=True)
                  child.wait()
                  log.seek(0)
                  out = log.read()
              if timed_out:
                  return 124, out + "\ntimed out after %d s" % ROW_SECONDS
              return child.returncode, out
          def result(name, state):
              with open(os.environ.get("REGRESSION_RESULTS") or os.devnull, "a") as handle:
                  handle.write("%s\t%s\n" % (name, state))
          gh("label", "create", "regression", "--force", "--description", "A regression row is failing")
          gh("label", "create", "defect", "--description", "A test that guards it is failing")
          guards = {cells[1]: cells for cells in rows(os.environ.get("REGRESSION_MAP") or os.devnull) if len(cells) > 4}
          out = gh("api", "--paginate", "repos/{owner}/{repo}/issues?state=open&labels=regression&per_page=100", "--jq",
                   '.[] | select(.pull_request == null) | {number, state: "OPEN", body, labels}')  # gh issue list stops at 1000
          issues = [json.loads(line) for line in out.stdout.splitlines() if line] if out.returncode == 0 else None
          if issues is None:
              print("NOTE: can't read issues, so none changed: " + out.stderr.strip()[:200])
          FEATURES = {row[0] for row in rows(".loop/docs.tsv") if row and row[0] and row[0] != "Home"}
          try:
              LABELS_ON = json.load(open(".loop/config.json")).get("feature_labels") is True
          except (OSError, ValueError, AttributeError):
              LABELS_ON = False
          failed, filed = [], [0]
          CLEANUP, halt = os.environ.get("REGRESSION_CLEANUP") == "true", []
          def write(what, *args, body=None):
              if halt or CLEANUP and time.time() - start > JOB_SECONDS - 120:
                  return halt and failed.append(what)
              if CLEANUP:
                  time.sleep(float(os.environ.get("REGRESSION_PACE") or 20))
              done = gh(*args, body=body)
              if done.returncode:
                  failed.append(what)
                  halt.extend(["rate limit"] * ("rate limit" in done.stderr.lower()))
                  print("FAILED %s: %s (FILE_FAILED)" % (what, done.stderr.strip()[:160]))
              else:
                  filed[0] += 1
              return done
          def label_for(page):  # the page's label, made first, or ""
              if not LABELS_ON or page not in FEATURES:
                  return ""
              label = "feature:" + "".join(c for c in page if c != "," and c.isprintable())[:42]
              made = gh("label", "create", label, "--force", "--description", "Issues about one feature")
              if made.returncode:
                  print("FAILED label %s: %s" % (label, made.stderr.strip()[:160]))
                  return ""
              return label
          FOUND = re.compile(r"<!-- loop-regression (\S+?)(?: placed=(\S*))? -->")
          def marked(body):
              match = FOUND.search(body or "")
              return (match.group(1), urllib.parse.unquote(match.group(2) or "")) if match else (None, "")
          red, start, dupes = [], time.time(), [600 if CLEANUP else 20]
          with open(os.environ.get("REGRESSION_RESULTS") or os.devnull, "w") as handle:
              handle.write("# started %d\n" % start)
          mine, seen = (os.environ.get("REGRESSION_SHARD") or "0/1").split("/"), 0
          mine, shards = int(mine[0]), int(mine[1])
          for row in rows(".loop/regression.tsv"):
              if len(row) < 3 or not wanted(row):
                  continue
              seen += 1
              if (seen - 1) % shards != mine:
                  continue
              if CLEANUP and time.time() - start > JOB_SECONDS - 120:
                  break
              if CLEANUP:
                  code, said, skipped = 125, "", True
              elif time.time() - start + ROW_SECONDS > JOB_SECONDS:
                  code, said, skipped = 125, "skipped: out of job time; this row did not run", True
              else:
                  (code, said), skipped = run(row[2]), False
              hits = sorted((item for item in issues or [] if marked(item["body"])[0] == row[0]), key=lambda i: i["number"])
              sk = lambda i: (i["body"] or "").split("\n")[1:2] == ["The row `%s` was skipped." % row[0]]
              hit = next((i for i in hits if i["state"] == "OPEN" and not sk(i)), None) or next(
                  (i for i in hits if i["state"] == "OPEN"), hits[0] if hits else None)
              for item in [i for i in hits if i["state"] == "OPEN" and i is not hit]:
                  if dupes[0] > 0:
                      dupes[0] -= 1
                      write("close duplicate #%d" % item["number"], "issue", "close", str(item["number"]), "--comment",
                            "Duplicate of #%d, kept for row %s." % (hit["number"], row[0]))
              state = "PASS" if code == 0 else "SKIPPED" if skipped or code == 77 else "KNOWN" if row[0] in known else "FAIL"
              print(state, row[0])
              result(row[0], state)
              if code == 0:
                  if hit and hit["state"] == "OPEN":
                      write("close #%d" % hit["number"], "issue", "close", str(hit["number"]), "--comment", "Passing again.")
              elif skipped:
                  for item in hits:
                      if item["state"] == "OPEN" and sk(item) and dupes[0] > 0:
                          dupes[0] -= 1
                          write("close skipped #%d" % item["number"], "issue", "close", str(item["number"]), "--comment",
                                "Closed: a skipped row files no issue.")
              elif row[0] not in known and code != 77:  # 77: cannot run here (SKIPPED)
                  red.append(row[0])
                  if issues is None:
                      continue
                  cells = guards.get(row[0]) or [""] * 5
                  label = label_for(cells[0])
                  mark = "<!-- loop-regression %s placed= -->" % row[0]
                  about = "- Feature: %s\n- Guards: %s\n- Checks: %s\n\n" % (cells[0] or "-", cells[3] or "-", cells[4] or "-")
                  body = "%s\nThe row `%s` %s.\n\n%s```\n%s\n```\n" % (mark, row[0], "fails", about,
                                                                 said[-1500:].replace("`" * 3, "'" * 3))
                  if not hit:
                      make = ["issue", "create", "--title", "Regression: " + row[0], "--label", "regression", "--label", "defect"]
                      made = gh(*make, *(["--label", label] if label else []), body=body)
                      if made.returncode and label and "label" in made.stderr.lower():
                          print("FAILED label %s: %s" % (label, made.stderr.strip()[:160]))
                          made = gh(*make, body=body)
                      if made.returncode:
                          failed.append("issue for " + row[0])
                          print("FAILED issue for %s: %s (FILE_FAILED)" % (row[0], made.stderr.strip()[:160]))
                      else:
                          filed[0] += 1
                  else:
                      n = str(hit["number"])
                      names = [label.get("name") for label in hit.get("labels") or []]
                      if hit["state"] != "OPEN":
                          write("reopen #" + n, "issue", "reopen", n)
                      if sk(hit):
                          write("body #" + n, "issue", "edit", n, body=body)
                      if "defect" not in names:
                          write("label #" + n, "issue", "edit", n, "--add-label", "defect")
                      if label and label not in names:
                          write("feature label #" + n, "issue", "edit", n, "--add-label", label)
                      write("comment #" + n, "issue", "comment", n, body="Still failing.")
          if TARGET == "nightly" and not CLEANUP:
              took, sha = int(time.time() - start), subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
              with open(os.environ.get("SUITE_TIME_FILE") or os.devnull, "w") as handle:
                  handle.write("%s\tfull\t%d\t%s\n" % (sha, took, time.strftime("%Y-%m-%d", time.gmtime())))
              print("SUITE_TIME %d" % took)
          if CLEANUP:
              ids = {row[0] for row in rows(".loop/regression.tsv") if row}
              for item in [i for i in issues or [] if i["state"] == "OPEN" and marked(i["body"])[0] not in ids | {None}]:
                  if dupes[0] > 0:
                      dupes[0] -= 1
                      write("close removed #%d" % item["number"], "issue", "close", str(item["number"]), "--comment",
                            "Closed: row removed from the regression table.")
              print("CLEANUP closed %d issues%s" % (filed[0], "; stopped: rate limit" * bool(halt)))
          if failed:
              print("FILED %d issue writes; FAILED %d: %s (FILE_FAILED)" % (filed[0], len(failed), ", ".join(failed)))
          sys.exit(1 if red or failed or CLEANUP and issues is None else 0)
          PY
      - name: Keep the full suite's time for the health job
        if: always() && steps.routine.outputs.on == 'true'
        continue-on-error: true
        uses: actions/upload-artifact@v4
        with:
          name: suite-time-${{ matrix.shard }}
          path: ${{ runner.temp }}/suite-time.tsv
          if-no-files-found: ignore
          retention-days: 30
      - name: Write the run summary, one table per feature
        if: always() && steps.routine.outputs.on == 'true'
        continue-on-error: true
        env:
          GH_TOKEN: ${{ github.token }}
          REGRESSION_RESULTS: ${{ runner.temp }}/regression-results.tsv
        run: |
          here=$(mktemp -d)
          cat > "$here/tests.py" <<'TESTS_PY_EOF'
@TESTS@
          TESTS_PY_EOF
          started=$(sed -n 's/^# started //p' "$REGRESSION_RESULTS" 2>/dev/null | head -n 1 || true)
          case "$started" in ''|*[!0-9]*) started=$(date +%s) ;; esac  # never an expression
          left=$(( started + 89 * 60 - $(date +%s) - 30 ))
          [ "$left" -ge 10 ] && timeout "$(( left < 60 ? left : 60 ))" python3 -I "$here/tests.py" issues --write >/dev/null || true
          took=$(( $(date +%s) - started ))
          GH_TOKEN= python3 -I "$here/tests.py" summary --results "$REGRESSION_RESULTS" --took "$took" >> "$GITHUB_STEP_SUMMARY" || {
            printf '## Regression\n\nThe grouped summary could not be written; see this step'"'"'s log.\n\n| Test | Result |\n|---|---|\n'
            grep -v '^#' "$REGRESSION_RESULTS" 2>/dev/null | awk -F'\t' '{print "| " $1 " | " $2 " |"}'
          } >> "$GITHUB_STEP_SUMMARY"
"""


HERE = os.path.dirname(os.path.abspath(__file__))
UNSAFE = ("${{", "@CRON@", "@ROWDROP@", "@TESTS@", "@SCHEDULE@", "@LEVELS@", "@BUDGET@", "@MATRIX@", "@SHARDS@", "TESTS_PY_EOF")


def render(cron, levels="nightly"):
    """The workflow text for this cron and ci_levels."""
    with open(os.path.join(HERE, "tests.py")) as handle:
        source = handle.read()
    bad = [token for token in UNSAFE if token in source]
    if bad:
        sys.exit("REFUSED: tests.py contains %s, which the workflow can't carry. Fix: reword that line" % bad[0])
    body = "\n".join(("          " + line).rstrip() for line in source.rstrip("\n").split("\n"))
    schedule = "" if cron == "off" else '  schedule:\n    - cron: "%s"\n' % cron
    return WORKFLOW.replace("@SCHEDULE@", schedule).replace("@CRON@", cron).replace("@LEVELS@", levels).replace("@ROWDROP@", repr(ROW_DROP)) \
        .replace("@BUDGET@", str(BUDGET_MINUTES)).replace("@SHARDS@", str(SHARDS)).replace("@MATRIX@", str(list(range(SHARDS)))) \
        .replace("@TESTS@", body)


def write(root, default):
    try:
        with open(os.path.join(root, ".loop", "config.json")) as handle:
            cfg = json.load(handle)
    except (OSError, ValueError):
        cfg = {}
    cfg = cfg if isinstance(cfg, dict) else {}
    cron, levels = cfg.get("regression_cron") or default, cfg.get("ci_levels") or "nightly"
    if levels not in ("land", "nightly"):
        sys.exit("REFUSED: ci_levels is %r, not land or nightly. Fix: edit .loop/config.json." % (levels,))
    if cron != "off" and not (isinstance(cron, str) and re.fullmatch(r"[0-9A-Za-z*/,\- ]+", cron) and len(cron.split()) == 5):
        sys.exit("REFUSED: regression_cron is not five cron fields or off. Fix: edit .loop/config.json.")
    path = os.path.join(root, ".github", "workflows", "regression.yml")
    if os.path.exists(path):
        with open(path) as handle:
            if not handle.read().startswith("# Written by workflow-regression"):
                sys.exit("REFUSED: %s exists, and this tool didn't write it. Fix: merge by hand." % path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as handle:
        handle.write(render(cron, levels))
    print("WROTE " + path)
    return 0
