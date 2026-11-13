#!/usr/bin/env python3
"""Batch merge (DEL-15): verify 3 or 4 ready pull requests together, merge them in one go, and name the culprit when it fails.

usage: mergebatch.py plan [--size N]        group the ready goals into batches of disjoint touches (default 3, at most 4)
       mergebatch.py run [--size N] [--merge]  verify each batch on one combined tree; --merge also runs merge.py per goal

A goal is ready when its run record is done, has a pull request, and is not held (hold_at / held_at). A batch holds goals whose
touches share no path, so one verification stands for all of them. `run` merges the batch's pull requests into a temporary
tree from origin/<base> and runs the check (config `batch_check`, default `regression.py run`) there. A failing batch splits:
each half is checked alone (a half checked alone that fails narrows to one goal), and the goal left is named, `CULPRIT slug`;
the goals that pass alone are merged. Without --merge nothing merges. merge.py still refuses a goal whose base moved
in paths its rows reach, so a batch never skips that check.
"""
import argparse
import glob
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def common():
    done = subprocess.run(["git", "rev-parse", "--git-common-dir"], capture_output=True, text=True)
    return os.path.join(os.path.abspath(done.stdout.strip() or ".git"), "loop")


def ready(runs):
    """[(slug, touches)] of the goals ready to merge, oldest record first."""
    found = []
    for path in sorted(glob.glob(os.path.join(runs, "*.json"))):
        try:
            with open(path) as handle:
                state = json.load(handle)
        except (OSError, ValueError):
            continue
        if isinstance(state, dict) and state.get("status") == "done" and state.get("pr") and not state.get("merged") \
                and not (state.get("hold_at") or state.get("held_at")) and state.get("release") != "ask":
            found.append((state.get("slug") or os.path.basename(path)[:-5], [str(t).strip("/") for t in state.get("touches") or []]))
    return found


def overlap(mine, theirs):
    """Same rule as the pr queue: any two paths equal or nested; no touches overlaps everything."""
    return not mine or not theirs or any(a == b or a.startswith(b + "/") or b.startswith(a + "/") for a in mine for b in theirs)


def group(goals, size=3):
    """Batches of at most `size` (at most 4) goals whose touches overlap none of their batch-mates', in order."""
    size, batches = max(1, min(int(size), 4)), []
    for slug, touches in goals:
        for batch in batches:
            if len(batch) < size and not any(overlap(touches, t) for _, t in batch):
                batch.append((slug, touches))
                break
        else:
            batches.append([(slug, touches)])
    return batches


def culprits(slugs, passes):
    """The goals that make `passes(list of slugs)` fail: [] when the batch passes; one slug when a single goal fails alone;
    a pair of halves that each pass but fail together is named as 'a+b'. Halves are checked alone, so a batch of n costs
    about 2*log2(n) more checks."""
    if passes(slugs):
        return []
    if len(slugs) == 1:
        return list(slugs)
    mid = len(slugs) // 2
    found = culprits(slugs[:mid], passes) + culprits(slugs[mid:], passes)
    return found or ["+".join(slugs)]  # each half passes alone: the failure is between them


def check_tree(base, slugs, command, states):
    """Merge the goals' branches into a temporary tree from origin/<base> and run the check there; True when it passes."""
    import tempfile
    temp = tempfile.mkdtemp(prefix="batch-")
    tree = os.path.join(temp, "tree")
    try:
        if subprocess.run(["git", "worktree", "add", "-q", "--detach", tree, "origin/" + base], capture_output=True).returncode:
            return False
        for slug in slugs:
            branch = states[slug].get("branch") or "loop/" + slug
            merged = subprocess.run(["git", "-C", tree, "-c", "user.name=batch", "-c", "user.email=batch@localhost", "merge", "--no-edit",
                                     "origin/" + branch], capture_output=True)
            if merged.returncode:
                return False
        return subprocess.run(command, cwd=tree, shell=isinstance(command, str)).returncode == 0
    finally:
        subprocess.run(["git", "worktree", "remove", "--force", tree], capture_output=True)


def main():
    parser = argparse.ArgumentParser(prog="mergebatch.py")
    parser.add_argument("command", choices=["plan", "run"])
    parser.add_argument("--size", type=int, default=3)
    parser.add_argument("--merge", action="store_true")
    args = parser.parse_args()
    runs = os.path.join(common(), "runs")
    goals = ready(runs)
    batches = group(goals, args.size)
    if not batches:
        print("NO BATCH: no goal is ready to merge")
        return 0
    for number, batch in enumerate(batches, 1):
        print("BATCH %d: %s" % (number, ", ".join(slug for slug, _ in batch)))
    if args.command == "plan":
        return 0
    states = {}
    for slug, _ in goals:
        with open(os.path.join(runs, slug + ".json")) as handle:
            states[slug] = json.load(handle)
    base = "main"
    try:
        with open(os.path.join(subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True).stdout.strip(),
                               ".loop", "config.json")) as handle:
            cfg = json.load(handle)
        base = cfg.get("base", "main")
    except (OSError, ValueError):
        cfg = {}
    command = cfg.get("batch_check") or [sys.executable, os.path.join(HERE, "..", "..", "workflow-regression", "scripts", "regression.py"), "run"]
    code = 0
    for number, batch in enumerate(batches, 1):
        slugs = [slug for slug, _ in batch]
        bad = culprits(slugs, lambda part: check_tree(base, part, command, states))
        for name in bad:
            print("CULPRIT %s: batch %d fails with it" % (name, number))
            code = 1
        good = [slug for slug in slugs if slug not in "+".join(bad).split("+")]
        print("BATCH %d %s: %s" % (number, "PASSES" if not bad else "SPLIT", ", ".join(good) or "nothing passes"))
        for slug in good if args.merge else []:
            done = subprocess.run([sys.executable, os.path.join(HERE, "merge.py"), slug])
            code = code or done.returncode
    return code


if __name__ == "__main__":
    sys.exit(main())
