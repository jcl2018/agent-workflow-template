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
            "REGRESSION_RESULTS", "REGRESSION_MAP", "RUNNER_TEMP")
LABELS = ("regression", "defect")  # the tool's own label, and the defect label every failing row's issue carries


def row_env():
    """A row's environment: no GitHub token, and no runner file a row could write into (the run summary, env, outputs)."""
    return {k: v for k, v in os.environ.items() if k not in ROW_DROP}


WORKFLOW = r"""# Written by workflow-regression. It reads .loop/regression.tsv and .loop/regression-known.tsv.
name: regression
on:
@SCHEDULE@  push:
    tags: ["v*"]
  workflow_dispatch:
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
          out = gh("issue", "list", "--label", "regression", "--state", "all", "--limit", "200", "--json", "number,state,body,labels,milestone")
          issues = json.loads(out.stdout or "[]") if out.returncode == 0 else None  # unread: change no issue, or each would repeat
          if issues is None:
              print("NOTE: can't read issues, so none changed: " + out.stderr.strip()[:200])
          FEATURES = {row[0] for row in rows(".loop/docs.tsv") if row and row[0] and row[0] != "Home"}  # milestone.py's features
          failed, filed = [], [0]
          def write(what, *args):  # every issue write is checked: a failure is named, and the step fails after the last row
              done = gh(*args)
              if done.returncode:
                  failed.append(what)
                  print("FAILED %s: %s (FILE_FAILED)" % (what, done.stderr.strip()[:160]))
              else:
                  filed[0] += 1
              return done
          def milestones():
              done = gh("api", "--paginate", "--slurp", "repos/{owner}/{repo}/milestones?state=all&per_page=100")
              try:
                  data = json.loads(done.stdout) if done.returncode == 0 else None
              except ValueError:
                  data = None
              if not isinstance(data, list):
                  return None  # unreadable: create nothing, let gh place issues by title
              flat = [m for page in data for m in (page if isinstance(page, list) else [page])]
              return {m["title"]: (m.get("number"), m.get("state") or "open") for m in flat if isinstance(m, dict) and m.get("title")}
          MILES = milestones() if issues is not None else {}
          READ = MILES is not None
          MILES = MILES or {}
          def place(feature):  # a docs.tsv feature's milestone, else Backlog; nothing else is ever created
              title = feature if feature in FEATURES else "Backlog"
              if title not in MILES and not READ:
                  return title, None
              if title not in MILES:
                  made = gh("api", "-X", "POST", "repos/{owner}/{repo}/milestones", "-f", "title=" + title)
                  try:
                      MILES[title] = (json.loads(made.stdout)["number"], "open")
                  except (ValueError, KeyError, TypeError):
                      MILES.update(milestones() or {})  # made meanwhile (422 already exists): read again
                      if title not in MILES:
                          failed.append("milestone " + title)
                          print("FAILED milestone %s: %s (FILE_FAILED)" % (title, made.stderr.strip()[:160]))
                          MILES[title] = (None, "failed")  # once per run
              number, state = MILES[title]
              if state == "failed":
                  return "", None
              return title, (number if state == "closed" else None)  # gh --milestone finds open ones; a closed one is set by number
          def by_number(number, closed, body):  # a closed milestone by number; on failure write back body (the placed= it had) so the next run retries
              if closed and number and write("milestone of #%s" % number, "api", "-X", "PATCH", "repos/{owner}/{repo}/issues/%s" % number,
                                             "-F", "milestone=%s" % closed).returncode:
                  write("placed of #%s" % number, "issue", "edit", str(number), "--body", body)
          FOUND = re.compile(r"<!-- loop-regression (\S+?)(?: placed=(\S*))? -->")
          def marked(body):
              match = FOUND.search(body or "")
              return (match.group(1), urllib.parse.unquote(match.group(2) or "")) if match else (None, "")
          red, start = [], time.time()
          with open(os.environ.get("REGRESSION_RESULTS") or os.devnull, "w") as handle:
              handle.write("# started %d\n" % start)
          for row in rows(".loop/regression.tsv"):
              if len(row) < 3 or row[1] not in ("land", "nightly"):
                  continue
              if time.time() - start + ROW_SECONDS > JOB_SECONDS:  # a row may run its full limit, so it must still fit
                  code, said, skipped = 125, "skipped: out of job time; this row did not run", True
              else:
                  (code, said), skipped = run(row[2]), False
              hits = [item for item in issues or [] if marked(item["body"])[0] == row[0]]
              hit = next((item for item in hits if item["state"] == "OPEN"), hits[0] if hits else None)
              state = "PASS" if code == 0 else "SKIPPED" if skipped else "KNOWN" if row[0] in known else "FAIL"
              print(state, row[0])
              result(row[0], state)
              if code == 0:
                  for item in hits:
                      if item["state"] == "OPEN":
                          gh("issue", "close", str(item["number"]), "--comment", "Passing again.")
              elif row[0] not in known:
                  red.append(row[0])
                  if issues is None:
                      continue
                  cells = guards.get(row[0]) or [""] * 5
                  title, closed = place(cells[0])
                  where, title = title, ("" if closed else title)
                  mark = "<!-- loop-regression %s placed=%s -->" % (row[0], urllib.parse.quote(where, safe=""))
                  about = "- Feature: %s\n- Guards: %s\n- Checks: %s\n\n" % (cells[0] or "-", cells[3] or "-", cells[4] or "-")
                  body = "%s\nThe row `%s` %s.\n\n%s```\n%s\n```\n" % (mark, row[0], "was skipped" if skipped else "fails", about,
                                                                 said[-1500:].replace("`" * 3, "'" * 3))
                  if not hit:
                      made = write("issue for " + row[0], "issue", "create", "--title", "Regression: " + row[0], "--label", "regression",
                                   "--label", "defect", "--body", body, *(["--milestone", title] if title else []))
                      by_number((re.findall(r"/issues/(\d+)", made.stdout) or [""])[-1], closed, FOUND.sub(lambda m: m.group(0).split(" placed=")[0] + " placed= -->", body, count=1))
                  else:
                      n = str(hit["number"])
                      if hit["state"] != "OPEN":
                          write("reopen #" + n, "issue", "reopen", n)
                      if "defect" not in [label.get("name") for label in hit.get("labels") or []]:
                          write("label #" + n, "issue", "edit", n, "--add-label", "defect")
                      now = (hit.get("milestone") or {}).get("title") or ""
                      if now == marked(hit["body"])[1] and where and where != now:  # still where the automation put it
                          old = FOUND.search(hit["body"]).group(0)
                          write("move #" + n, "issue", "edit", n, "--body", hit["body"].replace(old, mark), *(["--milestone", title] if title else []))
                          by_number(n, closed, hit["body"])
                      write("comment #" + n, "issue", "comment", n, "--body", "Skipped: out of job time; not run." if skipped else "Still failing.")
          if failed:
              print("FILED %d issue writes; FAILED %d: %s (FILE_FAILED)" % (filed[0], len(failed), ", ".join(failed)))
          sys.exit(1 if red or failed else 0)
          PY
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
UNSAFE = ("${{", "@CRON@", "@ROWDROP@", "@TESTS@", "@SCHEDULE@", "TESTS_PY_EOF")  # what Actions or this writer would read as its own


def render(cron):
    """The workflow text for this cron: what write() saves and the tests compare. It carries tests.py, the one
    test format, because the GitHub job has only the repo's own checkout."""
    with open(os.path.join(HERE, "tests.py")) as handle:
        source = handle.read()
    bad = [token for token in UNSAFE if token in source]
    if bad:
        sys.exit("REFUSED: tests.py contains %s, which the workflow can't carry. Fix: reword that line" % bad[0])
    body = "\n".join(("          " + line).rstrip() for line in source.rstrip("\n").split("\n"))
    schedule = "" if cron == "off" else '  schedule:\n    - cron: "%s"\n' % cron  # off: by hand only, and the run says so
    return WORKFLOW.replace("@SCHEDULE@", schedule).replace("@CRON@", cron).replace("@ROWDROP@", repr(ROW_DROP)) \
        .replace("@TESTS@", body)


def write(root, default):
    try:
        with open(os.path.join(root, ".loop", "config.json")) as handle:
            cron = json.load(handle).get("regression_cron") or default
    except (OSError, ValueError):
        cron = default
    if cron != "off" and not (isinstance(cron, str) and re.fullmatch(r"[0-9A-Za-z*/,\- ]+", cron) and len(cron.split()) == 5):
        sys.exit("REFUSED: regression_cron is not five cron fields or off. Fix: edit .loop/config.json.")
    path = os.path.join(root, ".github", "workflows", "regression.yml")
    if os.path.exists(path):
        with open(path) as handle:
            if not handle.read().startswith("# Written by workflow-regression"):
                sys.exit("REFUSED: %s exists, and this tool didn't write it. Fix: merge by hand." % path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as handle:
        handle.write(render(cron))
    print("WROTE " + path)
    return 0
