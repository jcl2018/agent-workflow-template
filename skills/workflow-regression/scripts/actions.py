#!/usr/bin/env python3
"""The GitHub Actions workflow regression.py workflow writes: it runs the rows on a schedule and keeps one issue per failing row."""
import json
import os
import re
import sys

# No terminal, no waiting: a prompt from git or gh must fail, not block.
os.environ.update(GIT_TERMINAL_PROMPT="0", GH_PROMPT_DISABLED="1", GIT_EDITOR="true", GIT_ASKPASS="true", SSH_ASKPASS="true")
if not sys.stdin or not sys.stdin.isatty():
    os.dup2(os.open(os.devnull, os.O_RDONLY), 0)

ROW_DROP = ("GH_TOKEN", "GITHUB_TOKEN", "GITHUB_STEP_SUMMARY", "GITHUB_ENV", "GITHUB_OUTPUT", "GITHUB_PATH", "GITHUB_STATE",
            "REGRESSION_RESULTS", "REGRESSION_MAP", "RUNNER_TEMP", "SUITE_TIME_FILE")


def row_env():
    """A row's environment: no GitHub token, and no runner file a row could write into (the run summary, env, outputs)."""
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
permissions:
  contents: read
  issues: write
  pull-requests: read  # the defect tests' pull request states
concurrency:
  group: regression
  cancel-in-progress: false
jobs:
  regression:
    runs-on: ubuntu-latest
    timeout-minutes: 90
    steps:
      - uses: actions/checkout@v4
        with:
          persist-credentials: false  # no token left in .git/config for a row to read
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - name: Check the routine
        id: routine
        env:
          EVENT: ${{ github.event_name }}
        run: |
          cron=$(python3 -c 'import json; print(json.load(open(".loop/config.json")).get("regression_cron") or "")' 2>/dev/null || true)
          if [ "$cron" = off ] && [ "$EVENT" = schedule ]; then  # off stops the schedule; a tag or a run by hand still runs
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
          SUITE_TIME_FILE: ${{ runner.temp }}/suite-time.tsv  # a full run's time, kept as artifact suite-time for health
          REGRESSION_TARGET: ${{ inputs.target }}  # a run by hand; checked below, never put into a shell line
          REGRESSION_LEVELS: "@LEVELS@"  # the schedule and v* tags run ci_levels
        run: |
          here=$(mktemp -d)  # a private folder: what each row guards, read before any row runs
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
          def wanted(row):  # a row id runs that row alone; land runs land rows; nightly runs land and nightly rows
              return row[0] == TARGET if TARGET not in ("land", "nightly") else row[1] in ("land", TARGET)
          def gh(*args):
              return subprocess.run(("gh",) + args, capture_output=True, text=True)
          def seconds(name, default):  # a bad or non-positive value falls back to the default
              try:
                  value = int(os.environ.get(name) or default)
              except ValueError:
                  return default
              return value if value > 0 else default
          ROW_SECONDS, JOB_SECONDS = seconds("REGRESSION_ROW_SECONDS", 900), seconds("REGRESSION_JOB_SECONDS", 88 * 60)
          ROW_ENV = {k: v for k, v in os.environ.items() if k not in @ROWDROP@}  # no token, no runner file a row could write into
          def run(command):  # own process group, output to a file: a row that times out fails alone and keeps what it printed
              with tempfile.TemporaryFile("w+", errors="replace") as log:
                  child = subprocess.Popen(command, shell=True, stdout=log, stderr=subprocess.STDOUT, env=ROW_ENV,
                                           start_new_session=True)
                  timed_out = False
                  try:
                      child.wait(timeout=ROW_SECONDS)
                  except subprocess.TimeoutExpired:
                      timed_out = True
                  try:
                      os.killpg(child.pid, 9)
                  except OSError:
                      pass
                  child.wait()
                  log.seek(0)
                  out = log.read()
              if timed_out:
                  return 124, out + "\ntimed out after %d s" % ROW_SECONDS
              return child.returncode, out
          def result(name, state):  # written as each row ends, so a job that runs out of time keeps what finished
              with open(os.environ.get("REGRESSION_RESULTS") or os.devnull, "a") as handle:
                  handle.write("%s\t%s\n" % (name, state))
          gh("label", "create", "regression", "--force", "--description", "A regression row is failing")
          gh("label", "create", "defect", "--description", "A test that guards it is failing")  # an existing one keeps its colour
          guards = {cells[1]: cells for cells in rows(os.environ.get("REGRESSION_MAP") or os.devnull) if len(cells) > 4}
          ISSUE_LIMIT = 5000  # gh pages through them itself; a list this long may be cut off
          out = gh("issue", "list", "--label", "regression", "--state", "all", "--limit", str(ISSUE_LIMIT), "--json", "number,state,body,labels")
          issues = json.loads(out.stdout or "[]") if out.returncode == 0 else None  # unread: change no issue, or each would repeat
          if issues is None:
              print("NOTE: can't read issues, so none changed: " + out.stderr.strip()[:200])
          elif len(issues) >= ISSUE_LIMIT:  # an older issue may be missing, so a row would open a duplicate: file nothing
              print("NOTE: the issue list may be cut off at %d, so none changed" % ISSUE_LIMIT)
              issues = None
          FEATURES = {row[0] for row in rows(".loop/docs.tsv") if row and row[0] and row[0] != "Home"}  # the pages
          try:  # the feature_labels setting (default off): only when true is a feature label made or set
              LABELS_ON = json.load(open(".loop/config.json")).get("feature_labels") is True
          except (OSError, ValueError, AttributeError):
              LABELS_ON = False
          failed, filed = [], [0]
          def write(what, *args):  # every issue write is checked: a failure is named, and the step fails after the last row
              done = gh(*args)
              if done.returncode:
                  failed.append(what)
                  print("FAILED %s: %s (FILE_FAILED)" % (what, done.stderr.strip()[:160]))
              else:
                  filed[0] += 1
              return done
          def label_for(page):  # the page's feature label, made first; "" when off, for no page, or if it can't be made
              if not LABELS_ON or page not in FEATURES:
                  return ""
              label = "feature:" + "".join(c for c in page if c != "," and c.isprintable())[:42]  # issues.feature_label
              made = gh("label", "create", label, "--force", "--description", "Issues about one feature")
              if made.returncode:
                  print("FAILED label %s: %s" % (label, made.stderr.strip()[:160]))
                  return ""
              return label
          FOUND = re.compile(r"<!-- loop-regression (\S+?)(?: placed=(\S*))? -->")  # placed= is written empty; older ones still parse
          def marked(body):
              match = FOUND.search(body or "")
              return (match.group(1), urllib.parse.unquote(match.group(2) or "")) if match else (None, "")
          red, start = [], time.time()
          with open(os.environ.get("REGRESSION_RESULTS") or os.devnull, "w") as handle:
              handle.write("# started %d\n" % start)
          for row in rows(".loop/regression.tsv"):
              if len(row) < 3 or not wanted(row):
                  continue
              if time.time() - start + ROW_SECONDS > JOB_SECONDS:  # a row may run its full limit, so it must still fit
                  code, said, skipped = 125, "skipped: out of job time; this row did not run", True
              else:
                  (code, said), skipped = run(row[2]), False
              hits = [item for item in issues or [] if marked(item["body"])[0] == row[0]]
              hit = next((item for item in hits if item["state"] == "OPEN"), hits[0] if hits else None)
              state = "PASS" if code == 0 else "SKIPPED" if skipped or code == 77 else "KNOWN" if row[0] in known else "FAIL"
              print(state, row[0])
              result(row[0], state)
              if code == 0:
                  for item in hits:
                      if item["state"] == "OPEN":
                          gh("issue", "close", str(item["number"]), "--comment", "Passing again.")
              elif row[0] not in known and code != 77 and not skipped:  # 77 or no job time left: SKIPPED, not a failure, so no issue
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
                      make = ["issue", "create", "--title", "Regression: " + row[0], "--label", "regression", "--label", "defect", "--body", body]
                      made = gh(*make, *(["--label", label] if label else []))
                      if made.returncode and label and "label" in made.stderr.lower():  # a refused label never loses the report
                          print("FAILED label %s: %s" % (label, made.stderr.strip()[:160]))
                          made = gh(*make)
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
                      if "defect" not in names:
                          write("label #" + n, "issue", "edit", n, "--add-label", "defect")
                      if label and label not in names:
                          write("feature label #" + n, "issue", "edit", n, "--add-label", label)
                      write("comment #" + n, "issue", "comment", n, "--body", "Still failing.")
          if TARGET == "nightly":  # the full suite's time (a cut-short run's too: at least that long) for health's REG-7 check
              took, sha = int(time.time() - start), subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
              with open(os.environ.get("SUITE_TIME_FILE") or os.devnull, "w") as handle:
                  handle.write("%s\tfull\t%d\t%s\n" % (sha, took, time.strftime("%Y-%m-%d", time.gmtime())))
              print("SUITE_TIME %d" % took)
          if failed:
              print("FILED %d issue writes; FAILED %d: %s (FILE_FAILED)" % (filed[0], len(failed), ", ".join(failed)))
          sys.exit(1 if red or failed else 0)
          PY
      - name: Keep the full suite's time for the health job
        if: always() && steps.routine.outputs.on == 'true'
        continue-on-error: true
        uses: actions/upload-artifact@v4
        with:
          name: suite-time
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
          here=$(mktemp -d)  # a new private folder: nothing a row left behind is on this script's import path
          cat > "$here/tests.py" <<'TESTS_PY_EOF'
@TESTS@
          TESTS_PY_EOF
          started=$(sed -n 's/^# started //p' "$REGRESSION_RESULTS" 2>/dev/null | head -n 1 || true)
          case "$started" in ''|*[!0-9]*) started=$(date +%s) ;; esac  # a number, or now: never an expression
          left=$(( started + 89 * 60 - $(date +%s) - 30 ))  # the rows end by minute 88; keep 30 s for the summary itself
          [ "$left" -ge 10 ] && timeout "$(( left < 60 ? left : 60 ))" python3 -I "$here/tests.py" issues --write >/dev/null || true
          took=$(( $(date +%s) - started ))
          GH_TOKEN= python3 -I "$here/tests.py" summary --results "$REGRESSION_RESULTS" --took "$took" >> "$GITHUB_STEP_SUMMARY" || {
            printf '## Regression\n\nThe grouped summary could not be written; see this step'"'"'s log.\n\n| Test | Result |\n|---|---|\n'
            grep -v '^#' "$REGRESSION_RESULTS" 2>/dev/null | awk -F'\t' '{print "| " $1 " | " $2 " |"}'
          } >> "$GITHUB_STEP_SUMMARY"
"""


HERE = os.path.dirname(os.path.abspath(__file__))
UNSAFE = ("${{", "@CRON@", "@ROWDROP@", "@TESTS@", "@SCHEDULE@", "@LEVELS@", "TESTS_PY_EOF")  # what Actions or this writer would read as its own


def render(cron, levels="nightly"):
    """The workflow text for this cron and ci_levels: what write() saves and the tests compare. It carries tests.py,
    the one test format, and its own row runner (the dispatch target's check too), because the GitHub job has only the
    repo's own checkout: an adopting repo has no skills/ folder."""
    with open(os.path.join(HERE, "tests.py")) as handle:
        source = handle.read()
    bad = [token for token in UNSAFE if token in source]
    if bad:
        sys.exit("REFUSED: tests.py contains %s, which the workflow can't carry. Fix: reword that line" % bad[0])
    body = "\n".join(("          " + line).rstrip() for line in source.rstrip("\n").split("\n"))
    schedule = "" if cron == "off" else '  schedule:\n    - cron: "%s"\n' % cron  # off: by hand only, and the run says so
    return WORKFLOW.replace("@SCHEDULE@", schedule).replace("@CRON@", cron).replace("@LEVELS@", levels).replace("@ROWDROP@", repr(ROW_DROP)) \
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
