#!/bin/bash
# reads: skills/workflow-monitoring/scripts/board_status.py skills/workflow-monitoring/scripts/graph.py
# reads: skills/workflow-monitoring/scripts/live_board.py skills/workflow-monitoring/scripts/status_graph.py
# Goal estimates from size and similar finished goals (issue 96) and stalled goals under Issues (issue 37), on a made-up
# repo of finished runs. No model is called. usage: test-estimates.sh [CHECK]  (no CHECK runs them all)
set -u
unset LOOP_SESSION_TOOL LOOP_OPERATION_SESSION LOOP_ROLE
here=$(cd "$(dirname "$0")/../.." && pwd)
T=$(mktemp -d)
export HOME="$T/home" LOOP_BOARD_HEALTH=green PYTHONDONTWRITEBYTECODE=1 PATH="$here/dev/toy/fakegh:$PATH" FAKE_GH_DIR="$T/gh"
mkdir -p "$HOME" "$T/gh"
cat > "$T/checks.py" <<'PY'
import datetime, json, os, shutil, subprocess, sys, tempfile, time
M = sys.argv[1]
sys.path.insert(0, M)
import board_status as bs, graph, live_board  # noqa: E402
AT = datetime.datetime(2026, 6, 1, 12, 0, 0, tzinfo=datetime.timezone.utc)
STEPS = bs.STEPS


def stamp(seconds):
    return (AT + datetime.timedelta(seconds=seconds)).strftime("%Y-%m-%dT%H:%M:%SZ")


class Repo:
    """A throwaway git repo with finished and running runs, goal files and a queue."""
    def __init__(self):
        self.root = tempfile.mkdtemp()
        subprocess.run(["git", "init", "-q", self.root], check=True)
        self.runs = os.path.join(self.root, ".git", "loop", "runs")
        os.makedirs(self.runs)
        os.makedirs(os.path.join(self.root, ".loop", "goals"))
        self.queue = []

    def goal(self, slug, d, a):
        done = "\n".join("%d. done line %d" % (i + 1, i + 1) for i in range(d))
        touches = ", ".join("area%d/file.txt" % i for i in range(a))
        with open(os.path.join(self.root, ".loop", "goals", slug + ".md"), "w") as handle:
            handle.write("# %s\n\n- Slug: %s\n- Touches: %s\n\n## Done lines\n\n%s\n\n## Verify by hand\n\n1. a step\n" % (slug, slug, touches, done))

    def done(self, slug, d, a, minutes, start=-200000):
        """A finished goal of size (d, a) whose steps took the given minutes (a number spreads it over all seven)."""
        per = minutes if isinstance(minutes, dict) else {s: minutes / len(STEPS) for s in STEPS}
        log, t = [stamp(start) + " frozen %d done lines" % d], start
        for step in STEPS:
            if step in per:
                t += per[step] * 60
                log.append(stamp(t) + " %s done in session" % step)
        self.write(slug, status="done", step="pr", release="merged", log=log, updated=stamp(t))
        self.goal(slug, d, a)

    def write(self, slug, **record):
        with open(os.path.join(self.runs, slug + ".json"), "w") as handle:
            json.dump(dict({"slug": slug, "goal": "Goal " + slug, "tries": 0, "pr": "", "waits_on": []}, **record), handle)

    def queued(self, slug, d, a):
        self.queue.append("- slug: %s | touches: %s | goal: G | %s" % (
            slug, ", ".join("area%d/f.txt" % i for i in range(a)), " | ".join("done: line %d" % i for i in range(d))))
        with open(os.path.join(self.root, ".loop", "queue.md"), "w") as handle:
            handle.write("# Goal queue\n\n" + "\n".join(self.queue) + "\n")

    def records(self):
        return [json.load(open(os.path.join(self.runs, f))) for f in sorted(os.listdir(self.runs)) if f.endswith(".json")]

    def board(self, at=AT):
        bs.MODEL.clear()
        return live_board.render(self.root, at)


def need(cond, why):
    if not cond:
        raise AssertionError(why)


def history(repo, size, totals, prefix):
    for i, minutes in enumerate(totals):
        repo.done("%s%d" % (prefix, i), size[0], size[1], minutes)


def est(repo, run):
    bs.MODEL.clear()
    return bs.estimate_full(run, repo.records(), AT, repo.root)


def check_area():
    cases = {"skills/workflow-monitoring/scripts/x.py": "skills/workflow-monitoring", "dev/toy/t.sh": "dev", ".github/workflows/x.yml": ".github",  # lanes: no read (path strings graph.area folds)
             "docs/wiki/Home.md": "docs", ".loop/docs.tsv": ".loop", "README.md": "README.md", "skills/*/SKILL.md": "skills",  # lanes: no read (path strings graph.area folds)
             "dev/toy/test-*.sh": "dev", "skills/README.md": "skills", "`./skills/workflow-docs/`": "skills/workflow-docs"}  # lanes: no read (path strings graph.area folds)
    for path, want in cases.items():
        need(graph.area(path) == want, "%s folds to %s, not %s" % (path, want, graph.area(path)))
    need(graph.size(["a", "b"], ["dev/toy", "dev/x", "README.md"]) == (2, 2) and graph.size([], ["x"]) is None, "size counts done lines and areas")


def check_size():
    repo = Repo()
    path = os.path.join(repo.root, ".loop", "goals", "g.md")
    with open(path, "w") as handle:
        handle.write("# g\n\n- Touches: a/x, b/y, c\n\n## Done lines\n\n1. one\n2. two\n```\n3. fenced\n```\n3. three\n\n## Verify by hand\n\n1. v\n2. v\n3. v\n4. v\n")
    need(bs.size_of({"slug": "g", "done": ["q"], "touches": ["z/1"]}, repo.root) == (3, 3), "the goal file wins: 3 done lines, 3 areas")
    need(bs.size_of({"slug": "h", "done": ["q", "r"], "touches": ["z/1"]}, repo.root) == (2, 1), "no goal file: the queue line's done and touches")
    with open(os.path.join(repo.root, ".loop", "goals", "n.md"), "w") as handle:
        handle.write("# n\n\n- Touches: a/x\n")
    need(bs.size_of({"slug": "n"}, repo.root) is None, "a goal file with no Done section and nothing else is unknown size")


def check_similar():
    repo = Repo()
    history(repo, (2, 1), [20, 22, 24, 26], "s")
    history(repo, (8, 8), [200, 210, 220, 230, 240, 250], "far")
    four = est(repo, {"slug": "q", "status": "queued", "done": ["x"] * 2, "touches": ["a/1"]})
    repo.done("s4", 2, 1, 28)
    five = est(repo, {"slug": "q", "status": "queued", "done": ["x"] * 2, "touches": ["a/1"]})
    need(four[3] and not five[3], "4 similar goals read rough, 5 do not: %s %s" % (four, five))
    need(19 * 60 <= five[0] <= 30 * 60, "with 5 similar goals the estimate comes from their times (20-28m): %s" % (five,))
    need(four[0] > 60 * 60, "with 4 similar goals it falls back to every finished goal (pooled, far larger): %s" % (four,))


def check_monotone():
    repo = Repo()
    history(repo, (3, 2), [30, 40, 50, 60, 70], "a")
    history(repo, (6, 4), [20, 25, 30, 35, 40], "b")
    sizes = [(2, 1), (4, 2), (7, 5)]
    found = [est(repo, {"slug": "q%d" % i, "status": "queued", "done": ["x"] * d, "touches": ["t%d/f" % k for k in range(a)]})[0]
             for i, (d, a) in enumerate(sizes)]
    need(found[0] < found[1] < found[2], "a larger goal gets a strictly longer estimate even when larger past goals were faster: %s" % found)


def check_lift_bound():
    repo = Repo()
    history(repo, (1, 1), [300, 320, 340, 360, 380], "slow")
    history(repo, (6, 6), [20, 22, 24, 26, 28], "quick")
    bs.MODEL.clear()
    runs = repo.records()
    big = {"slug": "q", "status": "queued", "done": ["x"] * 6, "touches": ["t%d/f" % k for k in range(6)]}
    left = bs.estimate(big, runs, AT, repo.root)[0]
    m = bs.model(runs, AT, repo.root)
    totals = [sum(b[0] for b in (bs.base(m["done"], (x, y), s)[0] for s in STEPS) if b) for x in range(1, 7) for y in range(1, 7)]
    need(left <= max(totals) + (6 + 6 - 2) * bs.STEP_UP + 1, "the lift is bounded by the largest smaller total plus STEP_UP per unit: %s" % left)
    need(left >= 300 * 60, "a large goal is never shorter than a smaller one: %s" % left)


def check_range_text():
    need(bs.estimate_text((1500, 1200, 2700, False)) == "20m to 45m left", bs.estimate_text((1500, 1200, 2700, False)))
    need(bs.estimate_text((1800, 1800, 1800, True)) == "30m to 30m left, rough", "both ends always show")
    need(bs.estimate_text((0, 0, 0, False)) == "<1m left" and bs.estimate_text(None) == "no estimate yet", "nothing left and no estimate")
    need(bs.spread([600]) == (600, 600, 600) and bs.spread([]) is None, "one time gives low = high; none gives no estimate")
    repo = Repo()
    history(repo, (2, 2), [30, 45, 60, 75, 600], "h")
    repo.queued("a-goal-with-a-rather-long-slug-name-here", 2, 2)
    lines = repo.board()
    need(all(len(line) <= live_board.WIDTH for line in lines), "every board line fits %d columns" % live_board.WIDTH)
    need(any("a-goal-with" in line and " to " in line for line in lines), "the queued goal shows a range")


def running(repo, slug, size, steps_done, step, since, status="running", extra=None):
    """A running goal of size that finished steps_done {step: minutes} and started step `since` seconds before AT."""
    t = -since - 60 * sum(steps_done.values())
    log = [stamp(t) + " frozen"]
    for s, minutes in steps_done.items():
        t += minutes * 60
        log.append(stamp(t) + " %s done in session" % s)
    log.append(stamp(-since) + " session report: worker: step %s, running" % step)
    repo.write(slug, status=status, step=step, log=log, updated=stamp(0), pid=1, **(extra or {}))
    repo.goal(slug, *size)


def check_pace():
    repo = Repo()
    history(repo, (3, 2), [{s: 10 for s in STEPS}] * 5, "h")
    running(repo, "slow", (3, 2), {"idea": 20, "plan": 20}, "build", 1)
    running(repo, "fast", (3, 2), {"idea": 5, "plan": 5}, "build", 1)
    running(repo, "crawl", (3, 2), {"idea": 100, "plan": 100}, "build", 1)
    plain = est(repo, {"slug": "q", "status": "queued", "done": ["x"] * 3, "touches": ["a/1", "b/1"]})[0] * 5 / 7
    got = {r["slug"]: est(repo, r)[0] for r in repo.records() if r["slug"] in ("slow", "fast", "crawl")}
    slow, fast, crawl = got["slow"], got["fast"], got["crawl"]
    need(fast < plain < slow, "pace scales the steps left: %s %s %s" % (fast, plain, slow))
    need(slow < crawl and abs(crawl / plain - 2) < 0.1, "pace is clamped at 2 (10x slower reads as 2x): %s %s %s" % (crawl, slow, plain))
    need(abs(fast / plain - 0.5) < 0.05, "pace 0.5 halves it: %s vs %s" % (fast, plain))


def check_overrun_range():
    repo = Repo()
    history(repo, (3, 2), [{s: m for s, m in zip(STEPS, (5, 10, 20, 30, 40, 50, 60))}, {s: m for s, m in zip(STEPS, (6, 12, 24, 36, 48, 60, 72))},
                           {s: m for s, m in zip(STEPS, (7, 14, 28, 42, 56, 70, 84))}, {s: m for s, m in zip(STEPS, (8, 16, 32, 48, 64, 80, 96))},
                           {s: m for s, m in zip(STEPS, (9, 18, 36, 54, 72, 90, 108))}], "h")
    for since in (60, 27 * 60, 28 * 60, 29 * 60, 200 * 60):
        running(repo, "r", (3, 2), {"idea": 7, "plan": 14}, "build", since)
        left, low, high, _ = est(repo, [r for r in repo.records() if r["slug"] == "r"][0])[:4]
        need(0 <= low <= left <= high, "0 <= low <= left <= high at %ss into build: %s %s %s" % (since, low, left, high))


def check_offflow():
    repo = Repo()
    history(repo, (3, 2), [{s: 10 for s in STEPS}] * 5, "h")
    log = [stamp(-1600) + " frozen", stamp(-1000) + " idea done", stamp(-400) + " plan done", stamp(-300) + " session report: worker: step build, running",
           stamp(-100) + " checks: lane land running"]
    repo.write("c", status="running", step="checks", log=log, updated=stamp(0))
    repo.goal("c", 3, 2)
    run = [r for r in repo.records() if r["slug"] == "c"][0]
    need(bs.current(run) == STEPS.index("build"), "a goal at checks after build is at build, not idea: %s" % bs.current(run))
    left = est(repo, run)[0]
    fresh = est(repo, {"slug": "q", "status": "queued", "done": ["x"] * 3, "touches": ["a/1", "b/1"]})[0]
    need(left < fresh * 5 / 7 + 60, "it is estimated from build onward, never from idea: %s vs a fresh goal's %s" % (left, fresh))
    stale = dict(run, reports=[{"step": "build", "at": stamp(-4000)}], log=log + [stamp(-50) + " review: started"])
    need(bs.current(stale) == STEPS.index("review"), "a newer log entry beats an older report")
    need(bs.current({"slug": "q", "status": "queued"}) == 0, "a queued goal is at idea")


def check_offflow_done():
    # Regression: a goal at checks after "review done" read as on review, so its qa time never counted and it never stalled
    repo = Repo()
    history(repo, (3, 2), [{s: 10 for s in STEPS}] * 5, "h")
    log = [stamp(-9000) + " frozen", stamp(-8400) + " idea done", stamp(-7800) + " plan auto-approved: x", stamp(-7200) + " build done",
           stamp(-6600) + " review done in session"]
    repo.write("rd", status="running", step="checks", log=log, updated=stamp(0), pid=1, flow={"review": "done"})
    repo.goal("rd", 3, 2)
    run = [r for r in repo.records() if r["slug"] == "rd"][0]
    need(bs.current(run) == STEPS.index("qa"), "a goal at checks after review done is at qa: %s" % bs.FLOW[bs.current(run)])
    need("- rd is stalled: qa has run 1h50m" in "\n".join(repo.board()), "its qa time counts, so it stalls past 3x")


def check_flow_seconds():
    log = [stamp(-4000) + " frozen", stamp(-3400) + " idea done", stamp(-3000) + " session report: worker: step plan, running",
           stamp(-2800) + " plan done", stamp(-2700) + " session report: worker: step build, running", stamp(-2000) + " report: half way",
           stamp(-1500) + " stopped: owner paused it", stamp(-500) + " session report: worker: step build, running", stamp(-100) + " checks: land"]
    got = bs.flow_seconds({"slug": "x", "status": "running", "step": "checks", "log": log}, AT)
    need(got.get("idea") == 600, "idea took 600s: %s" % got)
    need(got.get("plan") == 600, "plan took its 400s wait plus 200s: %s" % got)
    need(got.get("build") == 100 + 700 + 500 + 400 + 100, "build counts the mid-build report and checks gaps, not the stopped pause: %s" % got)


def check_stalled():
    repo = Repo()
    history(repo, (3, 2), [{s: 10 for s in STEPS}] * 5, "h")
    bs.MODEL.clear()
    running(repo, "st", (3, 2), {"idea": 10, "plan": 10}, "build", 1)
    est_build = bs.step_now([r for r in repo.records() if r["slug"] == "st"][0], repo.records(), AT, repo.root)[2]
    for since, want in ((3 * est_build - 1, False), (3 * est_build + 1, True)):
        running(repo, "st", (3, 2), {"idea": 10, "plan": 10}, "build", since)
        text = "\n".join(repo.board())
        need(("- st is stalled: build has run" in text) == want, "stalled only past 3x (%ss): %s" % (since, text[:400]))
    need("(estimate %s)" % bs.span(est_build) in text, "the stall line prints the estimate it compares against")
    running(repo, "st", (3, 2), {"idea": 10, "plan": 10}, "build", 10 * est_build, status="waiting", extra={"waiting": {"ask": "?"}})
    need("is stalled" not in "\n".join(repo.board()), "a waiting goal is never stalled")
    os.remove(os.path.join(repo.runs, "st.json"))
    repo2 = Repo()
    running(repo2, "lone", (3, 2), {}, "build", 99999)
    need("is stalled" not in "\n".join(repo2.board()), "a step with no estimate is never stalled")


def check_issue_96():
    repo = Repo()
    small, large = [10, 15, 20, 25, 30], [90, 105, 120, 135, 150]
    history(repo, (2, 1), small, "s")
    history(repo, (7, 5), large, "l")
    repo.queued("small-goal", 2, 1)
    repo.queued("large-goal", 7, 5)
    lines = repo.board()
    text = "\n".join(lines)
    bs.MODEL.clear()
    runs = repo.records()
    left = {}
    for slug, d, a, past in (("small-goal", 2, 1, small), ("large-goal", 7, 5, large)):
        item = dict(graph.parse([q for q in repo.queue if "slug: " + slug in q][0]), status="queued")
        found = bs.estimate(item, runs, AT, repo.root)
        need(min(past) * 60 <= found[0] <= max(past) * 60, "%s's estimate %s lies inside its similar goals' %s-%sm" % (slug, found[0], min(past), max(past)))
        need(not found[3], "%s has 5 similar goals, so it is not rough" % slug)
        need("- %s  %s" % (slug, bs.estimate_text(found)) in text, "%s shows its range on the board" % slug)
        left[slug] = found[0]
    need(left["small-goal"] != left["large-goal"] and left["small-goal"] < left["large-goal"], "two queued goals of different sizes differ: %s" % left)
    finish = [line for line in lines if line.startswith("finish about")]
    want = graph.clock(AT + datetime.timedelta(seconds=max(left.values())))
    need(finish and finish[0] == "finish about " + want, "the Finish line is at + the larger estimate: %s vs %s" % (finish, want))


def check_partial():
    repo = Repo()
    history(repo, (3, 2), [{"idea": 10, "plan": 10, "build": 10}] * 5, "h")
    repo.queued("p", 3, 2)
    text = "\n".join(repo.board())
    need("at least finish about" in text and "rough" in text, "a goal with steps that have no history makes the Finish line 'at least' and reads rough")


def check_unsafe_slug():
    repo = Repo()
    history(repo, (3, 2), [20] * 5, "h")
    need(bs.size_of({"slug": "../../etc/passwd"}, repo.root) is None, "a slug outside the pattern is unknown size")
    path = os.path.join(repo.root, ".loop", "goals", "locked.md")
    os.makedirs(path)
    need(bs.size_of({"slug": "locked"}, repo.root) is None, "an unreadable goal file is unknown size")
    found = est(repo, {"slug": "locked", "status": "queued"})
    need(found and found[3], "an unknown-size goal still gets a rough estimate: %s" % (found,))
    repo.queued("locked", 3, 2)
    need(any("locked" in line for line in repo.board()), "the board still renders")


def check_big_goal():
    repo = Repo()
    history(repo, (3, 2), [20, 25, 30, 35, 40], "h")
    repo.queued("huge", 60, 15)
    began = time.time()
    lines = repo.board()
    need(time.time() - began < 5, "a 60-line, 15-area goal renders quickly")
    need(any(line.startswith("- huge") and "rough" in line for line in lines), "a goal past every finished size reads rough")


def check_cache():
    repo = Repo()
    history(repo, (3, 2), [20] * 5, "h")
    run = {"slug": "q", "status": "queued", "done": ["x"] * 3, "touches": ["a/1", "b/1"]}
    first = bs.estimate(run, repo.records(), AT, repo.root)[0]
    for i in range(3):
        repo.done("h%d" % i, 3, 2, 90)
    rec = repo.records()
    second = bs.estimate(run, rec, AT, repo.root)[0]
    need(first != second, "a changed finished run changes the estimate in the same process: %s %s" % (first, second))


names = [n[6:] for n in sorted(globals()) if n.startswith("check_")]
pick = sys.argv[2:] or names
failed = 0
for name in pick:
    try:
        globals()["check_" + name.replace("-", "_")]()
        print("PASS: " + name)
    except Exception as error:  # noqa: BLE001  (a test reports every failure, whatever it is)
        failed += 1
        print("FAIL: %s: %s" % (name, str(error)[:600]))
print("== %d of %d checks failed" % (failed, len(pick)) if failed else "ALL PASS")
sys.exit(1 if failed else 0)
PY
cd "$T" && python3 "$T/checks.py" "$here/skills/workflow-monitoring/scripts" "$@"  # lanes: no read (the folder only goes on sys.path)
