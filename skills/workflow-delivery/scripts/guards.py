#!/usr/bin/env python3
"""Keep goals stopping only for real failures: format rules that bind only the steps started after them, refusals that
cost no try, the operation's repairs (resume, touches, a finding on a finished goal) and the data only they write.
Imported by goal.py (and role.begin); run only as `guards.py known`, which prints the rule ids as JSON.

  rules      RULES maps each format rule id to the release that added it. A step records the ids known when it started
             (state["rules_at"][step]); a rule binds the step only if its id is there. No rules_at: every rule binds.
  refusals   refuse_no_try: exit 2, tries, status, step and the ran marker untouched; the 5th in a row leaves a note.
  extra      <runs>/<slug>.extra.json: touches and findings only operation commands add, under an flock, so no writer
             of the run record can erase them.
"""
import datetime
import fcntl
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import role  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))

RULES = {"depth-line": "0.12.1", "depth-condensed": "0.12.1", "full-markers": "0.12.1"}
NOTE_AT, WAIT_AT = 5, 10  # refused records in a row before a board note, and before the owner is asked
FORMAT_RULE, NO_STEP_LINE, NOT_RUN_BY_FLOW = "FORMAT_RULE", "NO_STEP_LINE", "NOT_RUN_BY_FLOW"
WORKER_SELF_REPAIR, RESUME_STATUS, RESUME_NO_SESSION = "WORKER_SELF_REPAIR", "RESUME_STATUS", "RESUME_NO_SESSION"
RESUME_NO_WORKTREE, SESSION_TAKEN, DONE_LINES_CHANGED = "RESUME_NO_WORKTREE", "SESSION_TAKEN", "DONE_LINES_CHANGED"
TOUCHES_PATH, WAITING_OWNER, ANSWER_STATUS = "TOUCHES_PATH", "WAITING_OWNER", "ANSWER_STATUS"
REFUSALS = "refused records in a row"


def now():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def known():
    return sorted(RULES)


def stamp(state, step):
    """Record the rules known now as the ones step started under; a later start overwrites an earlier entry."""
    if not isinstance(state.get("rules_at"), dict):  # missing, or null in an older record
        state["rules_at"] = {}
    state["rules_at"][step] = known()


def applies(state, step, rule):
    held = (state.get("rules_at") or {}).get(step) if isinstance(state.get("rules_at"), dict) else None
    return held is None or rule in held


def named(rule):
    return "rule %s, added in v%s" % (rule, RULES[rule])


def check_record(state, step, text, cfg, result):
    """(stamp, refusal, ask, skipped) for a step that advances. refusal is (why, fix, code) and costs no try; ask is a
    question for the owner (a malformed flow file); skipped lists the rules a step started before and so isn't held to."""
    skipped = []

    def held(rule):
        if applies(state, step, rule):
            return True
        skipped.append("%s (v%s) not applied: %s started before it" % (rule, RULES[rule], step))
        return False

    setting = role.depth_of(cfg)
    ends = list(role.STEP.finditer(text))
    body = text[:ends[-1].start()] if ends else text
    found = role.DEPTH.findall(body)
    if not found:
        if held("depth-line"):
            return "", ("%s refused: no DEPTH line (%s)" % (step, named("depth-line")),
                        "write 'DEPTH: full' or 'DEPTH: condensed' on a line of its own just before the STEP line, then "
                        "record again", "%s depth-line" % FORMAT_RULE), None, skipped
        return " (depth not stated)", None, None, skipped
    depth = found[-1].lower()
    if step in ("plan", "review") and result != "skipped":
        if depth == "condensed" and setting == "full" and held("depth-condensed"):
            return "", ("the %s step ran condensed while review_depth is full (%s)" % (step, named("depth-condensed")),
                        "rerun the %s step at full depth, then record again" % step, "%s depth-condensed" % FORMAT_RULE), None, skipped
        if depth == "full" and held("full-markers"):
            wanted, bad = role.markers(step)
            if bad:
                return "", None, "%s: %s (the flow file's full_markers)" % (step, bad), skipped
            rest = "\n".join(line for line in body.splitlines() if not role.DEPTH.match(line)).lower()
            if any(m.lower() not in rest for m in wanted):
                return "", ("a configured full_markers evidence string for %s is missing from the reply (%s)" % (step, named("full-markers")),
                            "rerun the %s step at full depth, then record again" % step, "%s full-markers" % FORMAT_RULE), None, skipped
    state.setdefault("depth", {})[step] = depth
    return " (depth %s%s)" % (depth, ", skipped" if result == "skipped" else ""), None, None, skipped


def refuse_no_try(state, why, fix, code, save):
    """A refusal that changes nothing the goal depends on: no try is used and the goal keeps running. Only a counter is
    kept; at NOTE_AT in a row the run record's note says so, and the board shows it to the operation."""
    state["refusals"] = int(state.get("refusals") or 0) + 1
    if state["refusals"] >= WAIT_AT:  # a worker that can't fix its reply: the owner decides, never a silent loop
        state["status"], state["waiting"] = "waiting", {"ask": "%d %s: %s" % (state["refusals"], REFUSALS, why),
                                                        "words": ["go on " + state["slug"], "stop " + state["slug"]]}
    if state["refusals"] >= NOTE_AT:
        state["note"] = {"text": "%s: %d %s: %s" % (state.get("step") or "-", state["refusals"], REFUSALS, why), "at": now()}
    save(state, "refused (no try used): %s (%s)" % (why, code))
    print("REFUSED (no try used): %s. Fix: %s (%s)" % (why, fix, code))
    print("NEXT: " + fix)
    sys.exit(2)


def clear_refusals(state):
    state["refusals"] = 0
    if REFUSALS in str((state.get("note") or {}).get("text", "")):
        state["note"] = None


def revive(state, how, by, why):
    """The one revival of a failed or stopped goal (resume; sessions.py bind keeps the same fields, a toy test checks).
    Returns the log line."""
    state.update(status="running", tries=0, refusals=0, finding="", waiting=None, note=None, report=None)
    return "%s by %s: %s" % (how, by, " ".join(why.split())) if why else "%s by %s" % (how, by)


def extra_path(runs, slug):
    return os.path.join(runs, slug + ".extra.json")


def extra(runs, slug):
    try:
        with open(extra_path(runs, slug)) as handle:
            found = json.load(handle)
    except (OSError, ValueError):
        found = {}
    found = found if isinstance(found, dict) else {}
    return {key: list(found.get(key) or []) for key in ("touches", "findings", "log")}


def add_extra(runs, slug, key, item, line):
    """Append item to the sidecar's key and line to its log, under an exclusive lock, atomically."""
    with open(os.path.join(runs, slug + ".extra.lock"), "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        data = extra(runs, slug)
        data[key].append(item)
        data["log"].append("%s %s" % (now(), line))
        temp = extra_path(runs, slug) + ".%d.tmp" % os.getpid()
        with open(temp, "w") as handle:
            json.dump(data, handle, indent=2)
        os.replace(temp, extra_path(runs, slug))
    return data


def touches_of(runs, state):
    seen = list(state.get("touches") or [])
    return seen + [t for t in extra(runs, state["slug"])["touches"] if t not in seen]


def check_path(path, have):
    """None when PATH may widen touches, else the reason."""
    if not path or os.path.isabs(path) or ".." in path.split("/") or path.startswith("~") or re.search(r"[,|\s\x00-\x1f]", path):
        return "%r isn't a repo-relative path" % path
    if path.rstrip("/") in [t.rstrip("/") for t in have]:
        return "%s is already in the goal's touches" % path
    return None


def sync_touches(goal_file, touches):
    """Rewrite the goal file's '- Touches:' line from touches; True when it changed. The line isn't in the done-line hash."""
    try:
        with open(goal_file) as handle:
            text = handle.read()
    except OSError:
        return False
    line = "- Touches: " + (", ".join(touches) or "not declared")
    new = re.sub(r"^- Touches: .*$", lambda _: line, text, count=1, flags=re.M)
    if new == text:
        return False
    with open(goal_file, "w") as handle:
        handle.write(new)
    return True


def write_finding(g, state, text):
    line = "- %s: %s\n" % (state["slug"], " ".join(text.split()))
    path = os.path.join(g.root(), ".loop", "findings.md")
    g.write(path, line, "a")
    g.git("add", ".loop/findings.md")
    g.git("commit", "-m", "Finding: %s" % state["slug"], "--", ".loop/findings.md", check=False)
    push = g.run(["git", "push", "-u", "origin", "HEAD"])
    if push.returncode:
        print("NOTE: finding stays local, push failed: " + push.stderr.strip()[:200])


def fail_stop(g, state, text):
    state["status"] = "stopped"
    state["finding"] = text
    state["waiting"] = None
    g.save(state, "stopped: " + text)
    write_finding(g, state, text)
    print("STOPPED %s: %s" % (state["slug"], text))
    sys.exit(3)


def failed_try(g, state, why, step, fix):
    state["tries"] = state.get("tries", 0) + 1
    most = int(g.config().get("max_tries") or g.MAX_TRIES)
    if state["tries"] >= most:
        fail_stop(g, state, "Failed %d tries. Last: %s" % (state["tries"], why))
    state["step"] = step
    g.save(state, "try %d failed: %s" % (state["tries"], why))
    print("TRY %d OF %d FAILED: %s" % (state["tries"], most, why))
    print("NEXT: " + fix)


def cmd_wait(g, args):
    state = g.load(args.slug)
    state["status"] = "waiting"
    state["waiting"] = {"ask": args.ask, "words": args.words}
    g.save(state, "waiting: " + args.ask)
    print("WAITING %s: %s" % (args.slug, args.ask))
    return 0


def cmd_answer(g, args):
    state = g.load(args.slug)
    if state.get("status") != "waiting":
        g.no("%s is %s; answer only moves a waiting goal on. Fix: goal.py resume %s --why ... for a stopped one (%s)" % (
            args.slug, state.get("status"), args.slug, ANSWER_STATUS))
    state["status"] = "running"
    state["waiting"] = None
    g.save(state, "answered")
    print("ANSWERED %s" % args.slug)
    return 0


def waiting_gate(g, state):
    """A waiting goal can't record or open its pull request until the owner answers; that costs no try (exit 2)."""
    if state.get("status") == "waiting":
        sys.stderr.write("REFUSED (no try used): %s waits for the owner: %s. Fix: the operation answers (goal.py answer %s), "
                         "then try again (%s)\n" % (state["slug"], (state.get("waiting") or {}).get("ask") or "see the board",
                                                     state["slug"], WAITING_OWNER))
        sys.exit(2)


def advance(g, state):
    """After a recorded step: the next step starts under the rules known now, and the goal file's touches catch up."""
    left = [step for step in g.FLOW if step not in state.get("flow", {})]
    if left:
        stamp(state, left[0])
    sync_touches(g.goal_file(state["slug"]), touches_of(g.state_dir(), state))


def note_finding(runs, state, text):
    text = " ".join(text.split())
    add_extra(runs, state["slug"], "findings", {"at": now(), "text": text}, "finding (goal stays %s): %s" % (state["status"], text))
    print("FINDING recorded on %s (goal stays %s)" % (state["slug"], state["status"]))
    return 0


def operation_only(g, name, slug):
    if not g.SLUG.match(slug):
        g.no("bad slug %r" % slug)
    if os.environ.get("LOOP_ROLE") == "worker":
        g.no("a worker can't %s its own goal. Fix: ask the operation session (%s)" % (name, WORKER_SELF_REPAIR))


def cmd_resume(g, args):
    """The operation revives a failed or stopped goal for the session that owns it. Every check runs first; nothing is
    written on a refusal. It never starts a process."""
    operation_only(g, "resume", args.slug)
    state, slug = g.load(args.slug), args.slug
    if state.get("status") not in ("failed", "stopped"):
        g.no("%s is %s; only a failed or stopped goal resumes (%s)" % (slug, state.get("status"), RESUME_STATUS))
    sid = (state.get("session") or {}).get("id")
    if state.get("worker") != "session" or not sid:
        g.no("%s has no session. Fix: sessions.py bind %s ID (bind revives it), or watch.py resume %s for a background "
           "worker (%s)" % (slug, slug, slug, RESUME_NO_SESSION))
    tree = state.get("worktree") or ""
    try:
        if not os.path.isdir(tree):
            raise OSError(tree)
        text = g.read(os.path.join(tree, ".loop", "goals", slug + ".md"))
    except OSError:
        g.no("the goal's worktree or goal file is gone (%s). Fix: watch.py resume %s (%s)" % (tree, slug, RESUME_NO_WORKTREE))
    part = text.split("## Done lines", 1)[-1].split("\n## ", 1)[0]
    if g.done_sha([line.strip() for line in part.splitlines() if re.match(r"\s*\d+\. ", line)]) != state.get("done_sha"):
        sys.stderr.write("REFUSED: the done lines changed after they were frozen; a wrong done line needs a new goal (%s)\n" % DONE_LINES_CHANGED)
        return 1
    tool = os.path.join(HERE, "..", "..", "workflow-monitoring", "scripts", "sessions.py")
    took = g.run([sys.executable, tool, "reserve", slug, sid])
    if took.returncode:
        g.no((took.stderr or took.stdout).strip().replace("REFUSED: ", "") or "session %s can't be reserved (%s)" % (sid, SESSION_TAKEN))
    state = g.load(slug)  # recheck after the reservation: a stop that cleared meanwhile isn't revived
    if state.get("status") not in ("failed", "stopped") or (state.get("session") or {}).get("id") != sid:
        g.run([sys.executable, tool, "reserve", slug, sid, "--undo"])
        g.no("%s changed while resuming (now %s); nothing changed (%s)" % (slug, state.get("status"), RESUME_STATUS))
    note = revive(state, "resumed", args.by, args.why)
    try:
        g.save(state, note)
    except OSError as error:  # the run record didn't change: give the session back
        g.run([sys.executable, tool, "reserve", slug, sid, "--undo"])
        g.no("the run record couldn't be saved (%s); nothing changed" % error)
    message = "goal %s %s. Continue at %s in %s" % (slug, note, state.get("step") or "the next step", tree)
    sent = g.run([sys.executable, tool, "send", slug, message])
    if sent.returncode:
        print("RESUMED %s at %s (message not delivered)" % (slug, state.get("step")))
        print("NOTE: send failed; tell the session yourself: session %s; %s" % (sid, (sent.stdout + sent.stderr).strip()[:200]))
        print("NEXT: python3 %s send %s %s" % (os.path.abspath(tool), slug, json.dumps(message)))
        return 0
    print("RESUMED %s at %s" % (slug, state.get("step")))
    return 0


def cmd_touches(g, args):
    """The operation widens a goal's touches. Only the sidecar changes; the worker syncs the goal file itself."""
    operation_only(g, "widen touches of", args.slug)
    state = g.load(args.slug)
    bad = check_path(args.add, touches_of(g.state_dir(), state))
    if bad:
        g.no("%s (%s)" % (bad, TOUCHES_PATH))
    add_extra(g.state_dir(), args.slug, "touches", args.add, "touches +%s: %s" % (args.add, " ".join(args.why.split())))
    print("TOUCHES %s +%s" % (args.slug, args.add))
    return 0


if __name__ == "__main__":
    if sys.argv[1:] == ["known"]:
        print(json.dumps(known()))
        sys.exit(0)
    print("usage: guards.py known   print the format rule ids a step starting now is held to")
    sys.exit(0 if sys.argv[1:] in ([], ["-h"], ["--help"]) else 2)
