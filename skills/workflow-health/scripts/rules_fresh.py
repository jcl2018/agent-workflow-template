"""Freshness, Tests and Adoption rules (groups.py). Read-only; dates are days, so two runs on one day print the same lines.

  nightly           the newest recorded nightly run is older than a day (WARN; INFO when no nightly row exists)
  unreleased        commits after the newest v* tag, the oldest over 3 days old (WARN; INFO with no tag)
  finding-age       an open health issue older than 30 days (WARN; INFO when gh is not available here)
  skipped           a row recorded SKIPPED for over 7 days (WARN), from .loop/regression-runs.tsv
  network           a land row whose command reaches the network: curl, wget, http:// or https:// (WARN; fakegh is fine)
  config            .loop/config.json does not parse, or has no base (FAIL)
  checks-run-tests  the regression workflow exists but no land row does (WARN)
  template-version  VERSION is not the newest CHANGELOG heading (WARN; INFO when either is missing)
  scheduled         the regression or health workflow is missing, or has no schedule (WARN)
"""
import datetime
import json
import os
import re
import subprocess

# No terminal, no waiting: a prompt from git or gh must fail, not block.
os.environ.update(GIT_TERMINAL_PROMPT="0", GH_PROMPT_DISABLED="1", GIT_EDITOR="true", GIT_ASKPASS="true", SSH_ASKPASS="true")

import ghcache
from rules_trace import row, table


def today():
    return datetime.date.today()


def days_since(text):
    try:
        return (today() - datetime.date.fromisoformat(str(text)[:10])).days
    except ValueError:
        return None


def last_runs(root):
    """{row id: (status, date)} from .loop/regression-runs.tsv."""
    out = {}
    try:
        with open(os.path.join(root, ".loop", "regression-runs.tsv")) as handle:
            for line in handle:
                cells = line.rstrip("\n").split("\t")
                if line.strip() and not line.startswith("#") and len(cells) >= 3:
                    out[cells[0]] = (cells[1], cells[2])
    except OSError:
        pass
    return out


def nightly(root):
    ids = [item["id"] for item in table(root) if item["level"] == "nightly"]
    if not ids:
        return [row("INFO", "freshness", "nightly", "nightly", "no nightly rows")]
    runs = last_runs(root)
    dates = [runs[key][1] for key in ids if key in runs]
    newest = max(dates) if dates else ""
    age = days_since(newest) if newest else None
    if age is None or age > 1:
        return [row("WARN", "freshness", "nightly", "nightly", "the newest nightly run is %s" % (newest or "missing"),
                    "check that the nightly workflow runs", "nightly")]
    return []


def git(root, *args):
    done = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True)
    return done.stdout.strip() if done.returncode == 0 else ""


def unreleased(root):
    tag = git(root, "describe", "--tags", "--abbrev=0", "--match", "v*")
    if not tag:
        return [row("INFO", "freshness", "release", "unreleased", "no v* release tag")]
    dates = git(root, "log", "--format=%cs", "--reverse", tag + "..HEAD").splitlines()
    age = days_since(dates[0]) if dates else None
    if age is not None and age > 3:
        return [row("WARN", "freshness", tag, "unreleased", "%d commits since %s, the oldest from %s" % (len(dates), tag, dates[0]),
                    "cut a release (workflow-release)", tag)]
    return []


def finding_age(root):
    found, why = ghcache.issues(root)
    if found is None:
        return [row("INFO", "freshness", "findings", "finding-age", why)]
    return [row("WARN", "freshness", "#%d" % i["number"], "finding-age", "open since %s" % str(i.get("created_at"))[:10],
                "fix it or close it with triage", "#%d" % i["number"])
            for i in found if i.get("state") == "open" and ghcache.is_health(i) and (days_since(i.get("created_at")) or 0) > 30]


def skipped(root):
    return [row("WARN", "tests", key, "skipped", "skipped since %s" % date, "make it run again, or retire it", key)
            for key, (status, date) in sorted(last_runs(root).items())
            if status == "SKIPPED" and (days_since(date) or 0) > 7]


def network(root):
    hits = re.compile(r"\b(curl|wget)\s|https?://")
    return [row("WARN", "tests", item["id"], "network", "its command reaches the network", "use a stand-in (dev/toy/fakegh)", item["id"])
            for item in table(root) if item["level"] == "land" and hits.search(item["command"]) and "fakegh" not in item["command"]]


def config(root):
    path = os.path.join(root, ".loop", "config.json")
    try:
        with open(path) as handle:
            found = json.load(handle)
    except (OSError, ValueError) as error:
        return [row("FAIL", "adoption", ".loop/config.json", "config", "can't be read: %s" % str(error)[:80], "fix the JSON")]
    if not isinstance(found, dict) or not found.get("base"):
        return [row("FAIL", "adoption", ".loop/config.json", "config", "has no base branch", "set base (workflow-setup)")]
    return []


def checks_run_tests(root):
    if not os.path.exists(os.path.join(root, ".github", "workflows", "regression.yml")):
        return []
    if not any(item["level"] == "land" for item in table(root)):
        return [row("WARN", "adoption", "regression.yml", "checks-run-tests", "the regression workflow has no land row to run",
                    "add a land row (regression.py add)", "regression.yml")]
    return []


def template_version(root):
    try:
        version = open(os.path.join(root, "VERSION")).read().strip()
        head = re.search(r"^## v(\S+)", open(os.path.join(root, "CHANGELOG.md")).read(), re.M)
    except OSError:
        return [row("INFO", "adoption", "VERSION", "template-version", "no VERSION or CHANGELOG.md")]
    if head and head.group(1) != version:
        return [row("WARN", "adoption", "VERSION", "template-version", "VERSION %s, newest CHANGELOG heading v%s" % (version, head.group(1)),
                    "release again, or fix VERSION", "VERSION")]
    return []


def scheduled(root):
    out = []
    for name in ("regression.yml", "health.yml"):
        path = os.path.join(root, ".github", "workflows", name)
        text = open(path).read() if os.path.exists(path) else ""
        if "schedule:" not in text:
            out.append(row("WARN", "adoption", name, "scheduled", "missing" if not text else "has no schedule",
                           "write it (workflow-regression workflow, workflow-health workflow)", name))
    return out


FUNCTIONS = {"nightly": nightly, "unreleased": unreleased, "finding-age": finding_age, "skipped": skipped,
             "network": network, "config": config, "checks-run-tests": checks_run_tests,
             "template-version": template_version, "scheduled": scheduled}


def _c():
    import controls
    return controls


def f_nightly(root):
    c = _c(); c.repo(root)
    c.write(root, ".loop/regression.tsv", "# id\tlevel\tcommand\nn1\tnightly\ttrue\n")
    c.write(root, ".loop/regression-runs.tsv", "# id\tstatus\tdate\nn1\tPASS\t2000-01-01\n")


def f_unreleased(root):
    c = _c(); c.repo(root)
    c.git(root, "tag", "v0.1.0")
    c.write(root, "x.txt", "later\n")
    c.commit(root, "later", date="2000-01-02T00:00:00+0000")


def f_finding_age(root):
    c = _c(); c.repo(root)
    c.write(root, ".gh.json", json.dumps([{"number": 3, "title": "old", "state": "open", "labels": ["health"],
                                          "milestone": "Health", "created_at": "2000-01-01T00:00:00Z"}]))
    os.environ["LOOP_HEALTH_GH_FIXTURE"] = os.path.join(root, ".gh.json")
    ghcache.CACHE.clear()


def f_skipped(root):
    c = _c(); c.repo(root)
    c.write(root, ".loop/regression-runs.tsv", "# id\tstatus\tdate\nr1\tSKIPPED\t2000-01-01\n")


def f_network(root):
    c = _c(); c.repo(root)
    c.write(root, ".loop/regression.tsv", "# id\tlevel\tcommand\nr1\tland\tcurl https://example.test\n")


def f_config(root):
    c = _c(); c.repo(root)
    c.write(root, ".loop/config.json", "{not json")


def f_checks_run_tests(root):
    c = _c(); c.repo(root)
    c.write(root, ".github/workflows/regression.yml", "on:\n  schedule: []\n")


def f_template_version(root):
    c = _c(); c.repo(root)
    c.write(root, "VERSION", "1.0.1\n")
    c.write(root, "CHANGELOG.md", "# Changelog\n\n## v1.0.0 - 2000-01-01\n")


def f_scheduled(root):
    c = _c(); c.repo(root)


CONTROLS = {"nightly": ("freshness", "nightly", f_nightly), "unreleased": ("freshness", "unreleased", f_unreleased),
            "finding-age": ("freshness", "finding-age", f_finding_age), "skipped": ("tests", "skipped", f_skipped),
            "network": ("tests", "network", f_network), "config": ("adoption", "config", f_config),
            "checks-run-tests": ("adoption", "checks-run-tests", f_checks_run_tests),
            "template-version": ("adoption", "template-version", f_template_version),
            "scheduled": ("adoption", "scheduled", f_scheduled)}
