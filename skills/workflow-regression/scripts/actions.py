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
          import json, os, subprocess, sys, time
          def rows(path):
              if not os.path.exists(path):
                  return []
              return [line.rstrip("\n").split("\t") for line in open(path) if line.strip() and not line.startswith("#")]
          known = {row[0] for row in rows(".loop/regression-known.tsv")}
          def gh(*args):
              return subprocess.run(("gh",) + args, capture_output=True, text=True)
          ROW_SECONDS = int(os.environ.get("REGRESSION_ROW_SECONDS") or 900)
          def run(command):  # own process group: a row that times out fails alone and leaves no children behind
              child = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                                       errors="replace", start_new_session=True)
              try:
                  out, _ = child.communicate(timeout=ROW_SECONDS)
                  code = child.returncode
              except subprocess.TimeoutExpired:
                  out, code = "", 124
              try:
                  os.killpg(child.pid, 9)
              except OSError:
                  pass
              if code == 124:
                  try:  # bounded: a process outside the group may still hold the pipe
                      out, _ = child.communicate(timeout=10)
                  except subprocess.TimeoutExpired:
                      child.stdout.close()
                  out = (out or "") + "\ntimed out after %d s" % ROW_SECONDS
              return code, out
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
              if time.time() - start > 80 * 60:  # leave the 90-minute job time to finish; the rest is skipped and fails
                  red.append(row[0])
                  print("SKIP", row[0])
                  summary("| %s | SKIPPED: out of job time |" % row[0])
                  continue
              code, said = run(row[2])
              mark = "<!-- loop-regression %s -->" % row[0]
              hits = [item for item in issues if mark in item["body"]]
              hit = next((item for item in hits if item["state"] == "OPEN"), hits[0] if hits else None)
              state = "PASS" if code == 0 else "FAIL"
              print(state, row[0])
              summary("| %s | %s |" % (row[0], state))
              if code == 0:
                  for item in hits:
                      if item["state"] == "OPEN":
                          gh("issue", "close", str(item["number"]), "--comment", "Passing again.")
              elif row[0] not in known:
                  red.append(row[0])
                  body = "%s\nThe row `%s` fails.\n\n```\n%s\n```\n" % (mark, row[0], said[-1500:])
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
