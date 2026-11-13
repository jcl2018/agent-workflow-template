#!/bin/bash
# reads: skills/workflow-monitoring/scripts/board_status.py skills/workflow-monitoring/scripts/graph.py
# reads: skills/workflow-monitoring/scripts/live_board.py skills/workflow-monitoring/scripts/board_page.py
# reads: skills/workflow-monitoring/scripts/board_log.py skills/workflow-monitoring/scripts/board_model.py
# reads: skills/workflow-monitoring/scripts/board_report.py skills/workflow-health/scripts/milestone.py
# reads: skills/workflow-regression/scripts/lanes_cli.py
# Goal estimates from size and similar finished goals (issue 96), the backtest that picks the estimate model, held and
# stalled goals under Issues (issue 37), on a made-up repo of finished runs. No model is called. usage: test-estimates.sh [CHECK]  (no CHECK runs them all)
set -u
unset LOOP_SESSION_TOOL LOOP_OPERATION_SESSION LOOP_ROLE
here=$(cd "$(dirname "$0")/../.." && pwd)
. "$here/dev/toy/reap.sh"
T=$(mktemp -d)
export HOME="$T/home" LOOP_BOARD_HEALTH=green PYTHONDONTWRITEBYTECODE=1 PATH="$here/dev/toy/fakegh:$PATH" FAKE_GH_DIR="$T/gh"
mkdir -p "$HOME" "$T/gh"
cat > "$T/checks.py" <<'PY'
import contextlib, datetime, importlib.util, io, json, math, os, re, shutil, statistics, subprocess, sys, tempfile, time
M = sys.argv[1]
sys.path.insert(0, M)
import board_model as bm, board_status as bs, graph, live_board  # noqa: E402
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


def history(repo, size, totals, prefix, chronological=True):
    for i, minutes in enumerate(totals):
        repo.done("%s%d" % (prefix, i), size[0], size[1], minutes,
                  start=-20000000 + len(repo.records()) * 50000 if chronological else -20000000)


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
    history(repo, (6, 6), [20, 22, 24, 26], "quick")   # 9 finished goals: under MIN_BACKTEST, so the size rule is in use
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
    small, large = [10, 15, 20, 25, 30, 12], [90, 105, 120, 135, 150, 100]   # six each, out of time order, so the backtest has no earlier goals and the size rule stays the fallback
    history(repo, (2, 1), small, "s", chronological=False)
    history(repo, (7, 5), large, "l", chronological=False)
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



def check_worktree():
    repo = Repo()
    tree = os.path.join(repo.root, ".git", "loop", "worktrees", "w")
    outside = tempfile.mkdtemp()
    for base in (tree, outside):
        os.makedirs(os.path.join(base, ".loop", "goals"))
        with open(os.path.join(base, ".loop", "goals", "w.md"), "w") as handle:
            handle.write("# w\n\n- Touches: a/x, b/y\n\n## Done lines\n\n1. one\n2. two\n")
    bs.COMMON.clear()
    need(bs.size_of({"slug": "w", "worktree": tree}, repo.root) == (2, 2), "a running goal is sized from the goal file in its worktree")
    need(bs.size_of({"slug": "w", "worktree": outside}, repo.root) is None, "a worktree outside <common>/loop/worktrees is never read")


def check_similar_step():
    repo = Repo()
    history(repo, (2, 1), [{s: 10 for s in STEPS if s != "pr"}] * 5, "s")
    history(repo, (8, 8), [{s: 60 for s in STEPS}] * 5, "far")
    bs.MODEL.clear()
    m = bs.model(repo.records(), AT, repo.root)
    pr, similar = bs.base(m["done"], (2, 1), "pr")
    need(similar >= 5 and pr and pr[0] == 3600, "a step no similar goal logged comes from every finished goal: %s %s" % (pr, similar))
    build = bs.base(m["done"], (2, 1), "build")[0]
    need(build and build[0] == 600, "a step the similar goals logged comes from them: %s" % (build,))


def check_stall_held():
    repo = Repo()
    history(repo, (3, 2), [{s: 10 for s in STEPS}] * 5, "h")
    running(repo, "hd", (3, 2), {"idea": 10, "plan": 10}, "build", 6 * 3600)
    need("- hd is stalled" in "\n".join(repo.board()), "with a worker, a goal far past 3x is stalled")
    record = [r for r in repo.records() if r["slug"] == "hd"][0]
    record.pop("pid")
    repo.write("hd", **{k: v for k, v in record.items() if k != "slug"})
    text = "\n".join(repo.board())
    need("is stalled" not in text and "held" in text, "a held goal (no worker) is never called stalled: %s" % text[:400])


def report(repo, *args):
    """board_report.py on a fixture repo: (exit code, stdout, stderr)."""
    done = subprocess.run([sys.executable, os.path.join(M, "board_report.py"), "--root", repo.root, *args], capture_output=True, text=True)
    return done.returncode, done.stdout, done.stderr


def chooses(repo):
    """(backtest scores, n, chosen) as the board works them out."""
    bs.MODEL.clear()
    runs = live_board.load(repo.root)   # the board's own loader skips a garbled run file
    scores, n = bs.backtest(runs, AT, repo.root)
    return scores, n, bs.chosen(runs, AT, repo.root)


def set_a():
    """Time grows with size: (2,1) goals take 10-20m, (7,5) goals 100-200m; plus a garbled run file and a goal with no time."""
    repo = Repo()
    history(repo, (2, 1), [10, 12, 14, 16, 18, 20], "s")
    history(repo, (7, 5), [100, 120, 140, 160, 180, 200], "l")
    repo.write("idle", status="done", step="pr", log=[stamp(-100) + " frozen"], updated=stamp(0))
    with open(os.path.join(repo.runs, "garbled.json"), "w") as handle:
        handle.write("{not json")
    return repo


def check_backtest_best():
    a = set_a()
    b = Repo()   # same times in two size groups: the size rule's 60s lift per unit overshoots
    history(b, (4, 3), [{s: 1 for s in STEPS}] * 6, "s")
    history(b, (8, 6), [{s: 1 for s in STEPS}] * 6, "l")
    for name, repo, want in (("A", a, ("size",)), ("B", b, ("steps", "blend"))):
        scores, n, pick = chooses(repo)
        print("  set %s: n=%d %s chosen %s" % (name, n, {k: round(v, 3) for k, v in scores.items()}, pick))
        need(n == 11, "set %s: 11 goals score (the goal with no time is left out): %s" % (name, n))
        need(pick == min(bm.CANDIDATES, key=lambda c: (scores[c], bm.CANDIDATES.index(c))) and pick in want,
             "set %s: the board's model is the backtest's lowest score and %s: %s %s" % (name, want, pick, scores))
        code, out, err = report(repo, "--json")
        found = json.loads(out)
        need(code == 0 and found["chosen"] == pick and found["n"] == n, "set %s: board_report --json agrees: %s" % (name, out[:300]))
        need(all(c["time_ordered"]["score"] == c["score"] and c["leave_one_out"]["n"] == 12
                 for c in found["candidates"]), "the report marks the selector and keeps 12 leave-one-out diagnostics")
        code, text, _ = report(repo)
        need("chosen: %s, " % pick in text and "%d scorable goals" % n in text and "diagnostics: loo" in text,
             "set %s: the text says the same: %s" % (name, text[:300]))
    need(scores["size"] - scores["steps"] >= 0.1, "set B: the size rule is off by at least 0.1 more than step medians: %s" % scores)
    need("exact tie" in text, "set B: step medians and blend tie exactly and the tie goes to step medians: %s" % text)
    need("garbled.json" in report(a)[2] and "(BAD_RUN)" in report(a)[2] and "skipped 1 of" in report(a)[2], "a garbled run file is skipped with BAD_RUN")
    need(any(line.startswith("estimates: size rule") for line in a.board()), "the board renders past the garbled file")
    lone = Repo()
    lone.done("only", 3, 2, 20)
    need(chooses(lone)[1] == 0, "a goal no other finished goal can predict (zero prediction) is left out of scoring")
    hist = bs.History(bs.model(live_board.load(a.root), AT, a.root)["done"])
    bm.CELLS["none"] = lambda h, out: (lambda x, y: {s: None for s in STEPS})
    try:
        need(len(bs.folds(hist, ("steps",))) == 12 and bs.folds(hist, ("steps", "none")) == [], "a goal one candidate cannot estimate is dropped for all")
    finally:
        del bm.CELLS["none"]
    plain = tempfile.mkdtemp()
    done = subprocess.run([sys.executable, os.path.join(M, "board_report.py"), "--root", plain], capture_output=True, text=True)
    code, err = done.returncode, done.stderr
    need(code == 1 and "REFUSED: %s is not inside a git repo (NO_REPO)" % plain in err and "Pass --root" in err, "a folder outside git is refused: %s" % err)
    code, out, _ = report(Repo())
    need(code == 0 and "0 of 10 scorable goals" in out, "no finished runs is empty history, not an error: %s" % out)


def check_backtest_loo():
    repo = Repo()
    repo.done("g1", 1, 1, {"build": 10})
    repo.done("g2", 1, 1, {"build": 10})
    repo.done("g3", 5, 5, {"build": 20})
    bs.MODEL.clear()
    m = bs.model(repo.records(), AT, repo.root)
    rows = {r["slug"]: r for r in bs.folds(m["hist"])}
    # g3 left out: g1 and g2 took 600s; fewer than SIMILAR similar goals, so every cell is that pooled 600s, clamped at
    # (2, 2): size lifts 600 + 60 per unit, (2+2-2) + (5-2)+(5-2) units = 1080; step medians and blend lift 1s per unit = 608
    want = {"g3": {"size": 1080, "steps": 608, "blend": 608}, "g1": {"size": 900, "steps": 900, "blend": 900}}
    for slug, by in want.items():
        for name, value in by.items():
            need(abs(rows[slug]["left"][name] - value) < 1e-6, "%s left out, %s predicts %s, not %s" % (slug, name, value, rows[slug]["left"][name]))
    need(bs.table("size", m["hist"], (1, 1), "g1")[1][0] == 1, "g1 left out, one similar goal (g2) remains")
    hand = statistics.median([abs(math.log(900 / 600)), abs(math.log(900 / 600)), abs(math.log(608 / 1200))])
    need(abs(bs.score(list(rows.values()), "steps") - hand) < 1e-9, "the score is the median |log error| worked out by hand")


def check_time_order_selector():
    repo = Repo()
    for i in range(12):
        repo.done("g%d" % i, 1, 1, {"build": 10 if i < 10 else 20}, start=-100000 + i * 2000)
    old_names, old_cells, old_labels = bm.CANDIDATES, dict(bm.CELLS), dict(bm.LABELS)
    def cell(minutes):
        return lambda hist, out: lambda x, y: {s: (minutes * 60,) * 3 if s == "build" else None for s in STEPS}
    try:
        bm.CANDIDATES = ("future", "steady")
        bm.CELLS.update(future=lambda hist, out: cell(20 if len(hist.done) < 10 else 10)(hist, out), steady=cell(15))
        bm.LABELS.update(future="future", steady="steady")
        runs = repo.records()
        bm.MODEL.clear()
        loo = bm.folds(bm.model(runs, AT, repo.root)["hist"], bm.CANDIDATES)
        need(bs.score(loo, "future") < bs.score(loo, "steady"), "future model wins leave-one-out")
        scores, n = bm.backtest(runs, AT, repo.root)
        need(n == 11 and scores["steady"] < scores["future"], "time order rejects future-data model: n=%s scores=%s" % (n, scores))
        need(bm.chosen(runs, AT, repo.root) == "steady", "the board selects the time-ordered winner")
        need("time-ordered" in bm.accuracy_text(runs, AT, repo.root), "the board names the error's time order")
    finally:
        bm.CANDIDATES = old_names
        bm.CELLS.clear(); bm.CELLS.update(old_cells)
        bm.LABELS.clear(); bm.LABELS.update(old_labels)
        bm.MODEL.clear()


def check_time_order_edges():
    repo = Repo()
    # unique sizes: (1,1)=ga ... (7,7)=gi; times in seconds from AT, each goal's build takes 600
    for slug, size, start in (("ga", 1, -10000), ("gb", 2, -9000), ("ge", 3, -600), ("go", 4, -300), ("gt", 5, 0), ("gl", 6, 1000)):
        repo.done(slug, size, size, {"build": 10}, start=start)
    # inverted stamps: starts at 3000 but its entries are stamped 2000 and 2400, so finish < start and build still sums to 400
    log = [stamp(3000) + " frozen 7 done lines", stamp(2000) + " idea done in session", stamp(2400) + " build done in session"]
    repo.write("gi", status="done", step="pr", release="merged", log=log, updated=stamp(2400))
    repo.goal("gi", 7, 7)
    runs = repo.records()
    bm.MODEL.clear()
    hist = bm.model(runs, AT, repo.root)["hist"]
    need(sum(dict((s, t) for s, _, t in hist.done)["gi"].values()) > 0, "the inverted goal has logged time")
    seen, kept = {}, bm.table

    def spy(name, past, size, out=None):
        seen[size] = sorted(slug for slug, _, _ in past.done)
        return kept(name, past, size, out)
    bm.table = spy
    try:
        rows = bm.time_folds(runs, hist, bm.CANDIDATES)
    finally:
        bm.table = kept
        bm.MODEL.clear()
    want = {(2, 2): ["ga"], (3, 3): ["ga", "gb"], (4, 4): ["ga", "gb"], (5, 5): ["ga", "gb"],
            (6, 6): ["ga", "gb", "ge", "go", "gt"], (7, 7): ["ga", "gb", "ge", "gl", "go", "gt"]}
    need(seen == want, "each goal is predicted from exactly the goals finished strictly before it started: %s" % seen)
    need((1, 1) not in seen, "the first goal has no earlier goal, so no fold")
    need("ga" not in [r["slug"] for r in rows], "ga has no earlier goal, so it is never a fold")


def check_accuracy_line():
    repo = set_a()
    lines = repo.board()
    after = lines[lines.index("Finish") + 2]
    need(re.match(r"^estimates: size rule, time-ordered off x\d+\.\d \(11 goals\)$", after) and len(after) <= 60,
         "with 12 goals the line under the finish names the model and its error: %s" % after)
    few = Repo()
    history(few, (3, 2), [20, 30, 40, 50], "h")
    lines = few.board()
    need(lines[-1] == "estimates: size rule, error not known yet (3 of 10 goals)", "under 10 goals the error is not known yet: %s" % lines[-1])


def check_backtest_fails():
    repo = set_a()
    kept, err = bm.backtest, io.StringIO()

    def broken(*args):
        raise ValueError("bad fixture")
    bm.backtest = broken
    try:
        with contextlib.redirect_stderr(err):
            lines = repo.board()
    finally:
        bm.backtest = kept
    need(lines[-1] == "estimates: size rule, backtest failed (ValueError)", "a failing backtest falls back to the size rule: %s" % lines[-1])
    need("Traceback" in err.getvalue() and "bad fixture" in err.getvalue(), "its traceback goes to stderr: %s" % err.getvalue()[:200])


def check_stall_floor():
    repo = Repo()
    history(repo, (3, 2), [{s: 2 for s in STEPS}] * 5, "h")
    for minutes, want in ((10, False), (16, True)):
        running(repo, "sf", (3, 2), {"idea": 2, "plan": 2}, "build", minutes * 60)
        text = "\n".join(repo.board())
        need(("- sf is stalled" in text) == want, "a 2m step at %dm is %sstalled: %s" % (minutes, "" if want else "not ", text[:300]))


def held_log(*entries, status="done"):
    entries = ((-1000, "frozen"),) + entries
    return {"slug": "x", "status": status, "step": "build", "log": [stamp(t) + " " + text for t, text in entries]}


def check_pool_unread_stall():
    repo = Repo()
    history(repo, (3, 2), [{s: 10 for s in STEPS}] * 5, "h")
    running(repo, "hx", (3, 2), {"idea": 10, "plan": 10}, "build", 7200)
    record = [r for r in repo.records() if r["slug"] == "hx"][0]
    record["log"].append(stamp(-7000) + " session report: held at build for t (owner)")
    repo.write("hx", **{k: v for k, v in record.items() if k != "slug"})
    bs.MODEL.clear()
    runs = repo.records()
    lines = live_board.issues(runs, set(), repo.root, AT, None)
    need(not any("hx is stalled" in line for line in lines), "with the pool unreadable, a trailing hold entry stops the clock, so no stall: %s" % lines)
    need(any("hx is stalled" in line for line in live_board.issues(runs, set(), repo.root, AT, {})), "with the pool readable and the goal not held, it stalls")


def check_held_idle():
    repo = Repo()
    history(repo, (3, 2), [{s: 10 for s in STEPS}] * 5, "h")
    running(repo, "hd", (3, 2), {"idea": 10, "plan": 10}, "build", 600)
    record = [r for r in repo.records() if r["slug"] == "hd"][0]
    record.pop("pid")
    repo.write("hd", **{k: v for k, v in record.items() if k != "slug"})
    shown = [[line for line in repo.board(AT + datetime.timedelta(hours=h)) if line.startswith("- hd ")] for h in (0, 1)]
    need(shown[0] and shown[0] == shown[1], "a held goal's time left is the same an hour later: %s" % shown)
    run = [r for r in repo.records() if r["slug"] == "hd"][0]
    later = AT + datetime.timedelta(hours=1)
    need(bs.flow_seconds(run, later, True) == bs.flow_seconds(run, AT, True), "a held goal's step time stops")
    need(bs.flow_seconds(run, later, False)["build"] == bs.flow_seconds(run, AT, False)["build"] + 3600, "a goal not held keeps counting")
    for text in ("session report: held at plan for t (owner)", "session report: held before ship try 3 for t (owner)",
                 "session report: worker · t: review done (full); holding before qa as asked", "freed 1 session(s); slot released"):
        got = bs.flow_seconds(held_log((-900, "build: started"), (-600, text), (-300, "watch: note"), (-100, "build done")), AT, False)
        need(got.get("build") == 100 + 300, "%r pauses the gaps after it: %s" % (text, got))
    for text in ("session report: worker · board-held: frozen", "session report: no longer held, resuming",
                 "session report: no longer held at plan, resuming", "session report: was held at plan, now running", "session report: unheld at plan"):
        got = bs.flow_seconds(held_log((-900, "build: started"), (-600, text), (-300, "watch: note"), (-100, "build done")), AT, False)
        need(got.get("build") == 100 + 800, "%r pauses nothing: %s" % (text, got))
    got = bs.flow_seconds(held_log((-900, "idea done"), (-800, "session report: held at build for t (owner)"), (-700, "watch: note"),
                                   (-500, "start build"), (-200, "build done")), AT, False)
    need(got.get("plan") == 100 and got.get("build") == 300, "hold, watch note, start build, build done: idle and working told apart: %s" % got)
    got = bs.flow_seconds(held_log((-900, "idea done"), (-800, "freed 1 session(s); slot released"), (-700, "idle note"),
                                   (-600, "bound to session s1 (worker · x)"), (-500, "start build"), (-200, "build done")), AT, False)
    need(got.get("plan") == 200 and got.get("build") == 300, "free, idle note, bound to session, start build, done: the bind ends the pause: %s" % got)
    tail = held_log((-900, "build: started"), (-600, "session report: held at build for t (owner)"), status="running")
    need(bs.flow_seconds(tail, AT, False)["build"] == 100 + 300 + 600, "the pool readable and not held: the tail grows past a hold entry")
    need(bs.flow_seconds(tail, AT)["build"] == 100 + 300, "the pool unknown: a trailing hold entry stops the tail")


def check_module_size():
    for name in ("board_status", "board_log", "board_model", "board_report"):
        size = os.path.getsize(os.path.join(M, name + ".py"))
        need(size < 18432, "%s.py is %d bytes, not under 18,432" % (name, size))
    spec = importlib.util.spec_from_file_location("bs_by_path", os.path.join(M, "board_status.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    names = ("FLOW STEPS STEP_UP COMMON MODEL ASKING span base current estimate estimate_full estimate_text flow_seconds git model "
             "overrun size_of spread stall_lines step_now left_time read_json error_open wiki_check queued pr_states board_items "
             "seconds_by_step tokens_by_step step_left DOCS accuracy_text").split()
    need(not [n for n in names if not hasattr(module, n)], "every reader name resolves: %s" % [n for n in names if not hasattr(module, n)])
    need(bs.MODEL is bm.MODEL, "board_status.MODEL is the model's own dict")
    sys.path.insert(0, os.path.join(M, "..", "..", "workflow-health", "scripts"))
    import milestone as cost  # noqa: E402
    found = cost.board_status(os.path.join(M, "..", "..", "workflow-health", "scripts"))
    need(found is not None and hasattr(found, "seconds_by_step") and hasattr(found, "tokens_by_step"), "milestone.py loads board_status.py by path")
    top = os.path.join(M, "..", "..", "..")
    deps = subprocess.run([sys.executable, os.path.join(top, "skills/workflow-regression/scripts/lanes_cli.py"), "deps", "dev/toy/test-estimates.sh"],
                          cwd=top, capture_output=True, text=True).stdout
    need(all("scripts/%s.py" % n in deps for n in ("board_log", "board_model", "board_report")), "the test lanes follow the split: %s" % deps[:200])


def spread_history(repo, count, most):
    for i in range(count):
        d, a = 1 + i % most[0], 1 + (i // most[0]) % most[1]
        repo.done("g%d" % i, d, a, {s: 5 + (i * 7 + k * 3) % 40 for k, s in enumerate(STEPS)},
                  start=-20000000 + i * 50000)


def check_backtest_speed():
    repo = Repo()
    spread_history(repo, 100, (6, 5))
    runs = repo.records()
    bs.MODEL.clear()
    began = time.process_time()   # CPU seconds of this process: other tests running beside it do not count
    scores, n = bs.backtest(runs, AT, repo.root)
    took = time.process_time() - began
    print("  backtest over %d goals: %.2fs" % (n, took))
    need(n == 99 and took < 3, "the backtest over 100 finished goals takes under 3s: %.2fs" % took)
    big = Repo()
    spread_history(big, 300, (10, 8))
    began = time.process_time()
    big.board()
    took = time.process_time() - began
    print("  board over 300 goals: %.2fs" % took)
    need(took < 5, "the board over 300 finished goals renders under 5s: %.2fs" % took)


def check_steps_monotone():
    repo = Repo()
    history(repo, (3, 2), [30, 40, 50, 60, 70, 80], "a")
    history(repo, (6, 4), [20, 25, 30, 35, 40, 45], "b")
    bs.MODEL.clear()
    hist = bs.model(repo.records(), AT, repo.root)["hist"]
    total = lambda per: sum(b[0] for b in per.values() if b)
    for name in ("steps", "blend"):
        small, large = (total(bs.table(name, hist, size, "q")[0]) for size in ((2, 1), (4, 3)))
        need(small < large, "%s: a larger queued goal gets a strictly longer estimate: %s %s" % (name, small, large))
    cell = lambda x, y: {s: None for s in STEPS} if (x, y) == (2, 2) else {s: (60, 60, 60) for s in STEPS}
    per, _ = bs.envelope(cell, (2, 2), (9, 9), bs.TILT)
    need(total(per) >= 7 * 60 + 2 * bs.TILT, "an empty cell takes the lifted total, never below the envelope: %s" % per)


def check_recompute():
    repo = Repo()
    history(repo, (3, 2), [20, 30, 40, 50, 60, 70, 80, 90, 100, 110], "h")
    running(repo, "r", (3, 2), {"idea": 10}, "plan", 60)
    bs.MODEL.clear()
    runs = repo.records()
    first = bs.backtest(runs, AT, repo.root)
    need(bs.backtest(repo.records(), AT, repo.root) is first, "the same runs at the same time reuse the scores")
    repo.done("r", 3, 2, 50)
    second = bs.backtest(repo.records(), AT, repo.root)
    need(second is not first and second[1] == first[1] + 1, "a run that finishes recomputes the scores: %s %s" % (first[1], second[1]))


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
