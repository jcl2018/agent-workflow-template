#!/usr/bin/env python3
"""The GitHub Actions workflow regression.py workflow writes: it runs the rows on a schedule and keeps one issue per failing row."""
import json
import os
import sys

# No terminal, no waiting: a prompt from git or gh must fail, not block.
os.environ.update(GIT_TERMINAL_PROMPT="0", GH_PROMPT_DISABLED="1", GIT_EDITOR="true", GIT_ASKPASS="true", SSH_ASKPASS="true")
if not sys.stdin or not sys.stdin.isatty():
    os.dup2(os.open(os.devnull, os.O_RDONLY), 0)

WORKFLOW = r"""# Written by workflow-regression. It reads .loop/regression.tsv and .loop/regression-known.tsv.
name: regression
on:
  schedule:
    - cron: "@CRON@"
  push:
    tags: ["v*"]
  workflow_dispatch:
permissions:
  contents: read
  issues: write
concurrency:
  group: regression
  cancel-in-progress: false
jobs:
  regression:
    runs-on: ubuntu-latest
    timeout-minutes: 90
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - name: Run the rows, and keep one issue per failing row
        env:
          GH_TOKEN: ${{ github.token }}
        run: |
          python3 - <<'PY'
          import json, os, subprocess, sys, tempfile, time
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
          ROW_ENV = {k: v for k, v in os.environ.items() if k not in ("GH_TOKEN", "GITHUB_TOKEN")}  # rows never see the token
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
          def summary(text):  # written as each row ends, so a job that runs out of time keeps what finished
              with open(os.environ.get("GITHUB_STEP_SUMMARY") or os.devnull, "a") as handle:
                  handle.write(text + "\n")
          gh("label", "create", "regression", "--force", "--description", "A regression row is failing")
          out = gh("issue", "list", "--label", "regression", "--state", "all", "--limit", "200", "--json", "number,state,body")
          issues = json.loads(out.stdout or "[]")
          red, start = [], time.time()
          summary("## Regression rows\n\n| Row | Result |\n|---|---|")
          for row in rows(".loop/regression.tsv"):
              if len(row) < 3 or row[1] not in ("land", "nightly"):
                  continue
              if time.time() - start + ROW_SECONDS > JOB_SECONDS:  # a row may run its full limit, so it must still fit
                  code, said, skipped = 125, "skipped: out of job time; this row did not run", True
              else:
                  (code, said), skipped = run(row[2]), False
              mark = "<!-- loop-regression %s -->" % row[0]
              hits = [item for item in issues if mark in item["body"]]
              hit = next((item for item in hits if item["state"] == "OPEN"), hits[0] if hits else None)
              state = "PASS" if code == 0 else "SKIPPED" if skipped else "FAIL"
              print(state, row[0])
              summary("| %s | %s |" % (row[0], state))
              if code == 0:
                  for item in hits:
                      if item["state"] == "OPEN":
                          gh("issue", "close", str(item["number"]), "--comment", "Passing again.")
              elif row[0] not in known:
                  red.append(row[0])
                  body = "%s\nThe row `%s` %s.\n\n```\n%s\n```\n" % (mark, row[0], "was skipped" if skipped else "fails",
                                                               said[-1500:].replace("`" * 3, "'" * 3))
                  if not hit:
                      gh("issue", "create", "--title", "Regression: " + row[0], "--label", "regression", "--body", body)
                  else:
                      if hit["state"] != "OPEN":
                          gh("issue", "reopen", str(hit["number"]))
                      gh("issue", "comment", str(hit["number"]), "--body", "Still failing.")
          sys.exit(1 if red else 0)
          PY
"""


def write(root, default):
    try:
        with open(os.path.join(root, ".loop", "config.json")) as handle:
            cron = json.load(handle).get("regression_cron") or default
    except (OSError, ValueError):
        cron = default
    if len(cron.split()) != 5 or '"' in cron:
        sys.exit("REFUSED: regression_cron is not five cron fields. Fix: edit .loop/config.json.")
    path = os.path.join(root, ".github", "workflows", "regression.yml")
    if os.path.exists(path):
        with open(path) as handle:
            if not handle.read().startswith("# Written by workflow-regression"):
                sys.exit("REFUSED: %s exists, and this tool didn't write it. Fix: merge by hand." % path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as handle:
        handle.write(WORKFLOW.replace("@CRON@", cron))
    print("WROTE " + path)
    return 0
