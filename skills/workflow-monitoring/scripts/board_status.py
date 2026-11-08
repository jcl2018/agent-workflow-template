#!/usr/bin/env python3
"""The one status block: Needs you, Now, Next, Roadmap, Goals, always in that order.

usage: board_status.py [--html]

Prints the block as text, or with --html as a fragment the dashboard and board-artifact.html embed. Report, board and
dashboard all print this same content. Needs you comes first and is never hidden: every waiting, failed or stopped
worker, with the exact words to answer. Estimates come from the median of other runs' steps, read from their logs, and
read "no estimate yet" when there is none. Tokens read "unknown" until a run records them.
"""
import argparse
import datetime
import html
import json
import os
import re
import statistics
import subprocess
import sys

STEPS = ("idea", "plan", "build", "review", "qa", "ship", "pr")
ASKING = ("waiting", "failed", "stopped")
TITLES = ("Needs you", "Now", "Next", "Roadmap", "Goals")

# No terminal, no waiting: a prompt from git or gh must fail, not block.
os.environ.update(GIT_TERMINAL_PROMPT="0", GH_PROMPT_DISABLED="1", GIT_EDITOR="true", GIT_ASKPASS="true", SSH_ASKPASS="true")


def git(*args, cwd=None):
    done = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)
    return done.stdout.strip() if done.returncode == 0 else ""


def read_json(path):
    try:
        with open(path) as handle:
            return json.load(handle)
    except (OSError, ValueError):
        return None


def stamp(text):
    try:
        return datetime.datetime.fromisoformat(str(text).split(" ", 1)[0].replace("Z", "+00:00"))
    except ValueError:
        return None


def span(seconds):
    seconds = int(seconds)
    return "%dh%02dm" % divmod(seconds // 60, 60) if seconds >= 3600 else "%dm" % (seconds // 60) if seconds >= 60 else "<1m"


def tok(count):
    return "unknown" if count is None else "%dk" % round(count / 1000) if count >= 1000 else str(count)


def seconds_by_step(run, at):
    """Time each step took, from the gaps before its log entries, plus the gap since the last entry for the current step."""
    found, log = {}, run.get("log") or []
    for before, entry in zip(log, log[1:]):
        word = entry.split(" ", 2)[1] if entry.count(" ") else ""
        a, b = stamp(before), stamp(entry)
        if word in STEPS and a and b:
            found[word] = found.get(word, 0) + (b - a).total_seconds()
    last = stamp(log[-1]) if log else None
    if run.get("status") == "running" and run.get("step") in STEPS and last:
        found[run["step"]] = found.get(run["step"], 0) + max(0, (at - last).total_seconds())
    return found


def tokens_by_step(run):
    value = run.get("tokens")
    return {step: n for step, n in value.items() if step in STEPS and isinstance(n, int)} if isinstance(value, dict) else {}


def usual(runs, mine, step, pick):
    values = [pick(run).get(step) for run in runs if run["slug"] != mine["slug"] and run.get("status") == "done"]
    values = [v for v in values if v]
    return statistics.median(values) if values else None


def step_lines(run, runs, at):
    spent, used = seconds_by_step(run, at), tokens_by_step(run)
    here = STEPS.index(run["step"]) if run.get("step") in STEPS else 0
    lines, left, known = [], 0, False
    for index, step in enumerate(STEPS):
        est_t = usual(runs, run, step, lambda r: seconds_by_step(r, at))
        est_k = usual(runs, run, step, tokens_by_step)
        if index > here and est_t:
            left, known = left + est_t, True
        elif index == here and est_t:
            left, known = left + max(0, est_t - spent.get(step, 0)), True
        done = "actual %s, %s tokens" % (span(spent[step]) if step in spent else "-", tok(used.get(step))) if index <= here else "actual -"
        lines.append("    %-6s est %s, %s tokens | %s" % (step, span(est_t) if est_t else "no estimate yet",
                                                         tok(round(est_k)) if est_k else "no estimate yet", done))
    lines.append("    remaining steps: " + ("est %s" % span(left) if known else "no estimate yet"))
    return lines


def goal_lines(run, root):
    path = os.path.join(run.get("worktree") or root, ".loop", "goals", run["slug"] + ".md")
    try:
        with open(path) as handle:
            text = handle.read()
    except OSError:
        text = ""
    lines = re.findall(r"^(\d+)\. (.+)$", text.split("## Verify by hand")[0], re.M)
    met = {int(n) for n, _ in lines} if run.get("status") == "done" else set(run.get("met") or [])
    return ["- %s: %d of %d done lines met" % (run["slug"], len(met & {int(n) for n, _ in lines}), len(lines))] + \
        ["    [%s] %s. %s" % ("x" if int(n) in met else " ", n, line[:90]) for n, line in lines]


def queued(root, runs):
    names, found = {run["slug"] for run in runs}, []
    try:
        with open(os.path.join(root, ".loop", "queue.md")) as handle:
            for line in handle:
                match = re.match(r"- slug: ([a-z0-9-]+)", line)
                if match and match.group(1) not in names:
                    found.append(match.group(1))
    except OSError:
        pass
    return found


def bar(closed, total):
    full = round(10 * closed / total) if total else 0
    return "[%s%s] %d of %d" % ("#" * full, "-" * (10 - full), closed, total)


def roadmap(root):
    try:
        done = subprocess.run(["gh", "api", "repos/{owner}/{repo}/milestones?state=all&per_page=100"], cwd=root,
                              capture_output=True, text=True, timeout=20)
        found = json.loads(done.stdout) if done.returncode == 0 else []
    except (OSError, ValueError, subprocess.SubprocessError):
        found = []
    found = [item for item in found if isinstance(item, dict)]
    if not found:
        return ["(no milestone data)"]
    closed = sum(item.get("closed_issues", 0) for item in found)
    total = closed + sum(item.get("open_issues", 0) for item in found)
    return ["- %s %s" % (" ".join(str(item.get("title")).split()), bar(item.get("closed_issues", 0), item.get("closed_issues", 0) + item.get("open_issues", 0)))
            for item in found] + ["overall %s" % bar(closed, total)]


def sections(root=None, at=None):
    root = root or git("rev-parse", "--show-toplevel")
    at = at or datetime.datetime.now(datetime.timezone.utc)
    folder = os.path.join(os.path.abspath(os.path.join(root, git("rev-parse", "--git-common-dir", cwd=root))), "loop", "runs")
    runs = [read_json(os.path.join(folder, name)) for name in sorted(os.listdir(folder)) if name.endswith(".json")] if os.path.isdir(folder) else []
    runs = [run for run in runs if isinstance(run, dict) and run.get("slug") and run.get("status") != "retired"]
    needs, now, nxt = [], [], []
    for run in runs:
        report = (run.get("report") or {}).get("text", "")
        if run.get("wiki_error"):
            needs.append("- %s (wiki not published): %s" % (run["slug"], " ".join(str(run["wiki_error"]).split())[:200]))
        if run.get("release_error"):
            needs.append("- %s (release failed): %s" % (run["slug"], " ".join(str(run["release_error"]).split())[:200]))
        if run.get("status") in ASKING:
            ask = run.get("waiting") or {}
            words = ask.get("words") or ["resume " + run["slug"]]
            needs.append("- %s (%s): %s" % (run["slug"], run["status"], " ".join(str(ask.get("ask") or report or run.get("finding") or "see its log").split())[:200]))
            needs += ["    answer: " + w for w in words]
        elif run.get("status") == "running":
            now.append("- %s: step %s (stage %d of %d)%s" % (run["slug"], run.get("step") or "-", STEPS.index(run["step"]) + 1 if run.get("step") in STEPS else 0,
                                                              len(STEPS), (" - " + report) if report else ""))
            now += step_lines(run, runs, at)
        elif run.get("status") == "done" and (run.get("report") or {}).get("status") != "merged":
            nxt.append("- %s: %s" % (run["slug"], report or "pull request %s" % (run.get("pr") or "open")))
    nxt = ["- %s: queued" % slug for slug in queued(root, runs)] + nxt
    goals = [line for run in runs for line in goal_lines(run, root)]
    return list(zip(TITLES, [needs or ["(nothing needs you)"], now or ["(nothing running)"], nxt or ["(nothing queued)"], roadmap(root), goals or ["(no goals)"]]))


def text(parts):
    return "\n".join("== %s ==\n%s\n" % (title, "\n".join(lines)) for title, lines in parts)


def fragment(parts):
    e = html.escape
    return "".join("<section%s><h2>%s</h2><pre>%s</pre></section>" % (" class=wait" if title == "Needs you" else "", e(title), e("\n".join(lines)))
                   for title, lines in parts)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--html", action="store_true")
    args = parser.parse_args()
    parts = sections()
    sys.stdout.write(fragment(parts) if args.html else text(parts))
    return 0


if __name__ == "__main__":
    sys.exit(main())
