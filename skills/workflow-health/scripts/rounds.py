"""A round's state and cost, shared by automation.py (the digest) and mail.py (the email). It runs gh, nothing else.

The state marker ends the digest issue's body and each round's comment:
    <!-- automation-digest run=R open=N:M,N:M [mailing] [mailed] -->
R is a run id (digits, none or local), N an issue number, M its milestone number (0 for none), never a title, so no
title can break the comment. Tokens are read in any order; the old form `open=12,9 run=R` reads as milestone 0. The
flags `mailing` and `mailed` live only on a round's own comment: a later round never erases them.

A round is a health run and the newest regression run created before it, at most 6 hours before. Its job time (each
job's completedAt - startedAt; the health run counted so far) is flagged over 45 minutes (AUT-7). The spend counts
every regression and health run started since the previous round's health run, each job's minutes rounded up.
"""
import datetime
import glob
import html
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile

TITLE = "Automation digest"
BOTS = ("github-actions[bot]", "app/github-actions", "github-actions")  # REST login, gh's login, gh's short form
BUDGET_MINUTES = 45  # fixed by AUT-7, no setting
WINDOW = datetime.timedelta(hours=6)
RUN_LIMIT = 200
REG_LOOKBACK = 20  # regression runs searched for the round's own
JOB_READS = 30  # runs whose jobs the spend reads; more since the last round make it a lower bound
MARK = re.compile(r"<!-- automation-digest ([^<>]*?) -->")
RUN = re.compile(r"[0-9]+|none|local")
os.environ.update(GIT_TERMINAL_PROMPT="0", GH_PROMPT_DISABLED="1", GIT_EDITOR="true", GIT_ASKPASS="true", SSH_ASKPASS="true")


def gh(*args, body=None):
    """gh with a long text (body=) in a temp file passed as --body-file, never on the command line (Windows caps it)."""
    if body is not None:
        with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8", newline="\n") as f:
            f.write(body)
        args += ("--body-file", f.name)
    try:
        return subprocess.run(("gh",) + args, capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.SubprocessError) as err:
        return subprocess.CompletedProcess(args, 1, "", str(err))
    finally:
        if body is not None:
            os.remove(f.name)


def loads(done, default):
    try:
        return json.loads(done.stdout) if done.returncode == 0 and done.stdout.strip() else default
    except ValueError:
        return default


def parse(text):
    """The last state marker in text as {run, open: {n: m}, flags}, or None when there is none or it is malformed."""
    found = MARK.findall(text or "")
    if not found:
        return None
    state = {"run": None, "open": {}, "flags": set()}
    for token in found[-1].split():
        key, eq, value = token.partition("=")
        if not eq:
            if key in ("mailing", "mailed"):
                state["flags"].add(key)
            continue
        if key == "run":
            if not RUN.fullmatch(value):
                return None
            state["run"] = value
        elif key == "open":
            for item in filter(None, value.split(",")):
                number, _, milestone = item.partition(":")
                if not number.isdigit() or (milestone and not milestone.isdigit()):
                    return None
                state["open"][int(number)] = int(milestone or 0)
    return state if state["run"] else None


def marker(run, open_issues, flags=()):
    items = ",".join("%d:%d" % (n, open_issues[n]) for n in sorted(open_issues))
    extra = "".join(" " + flag for flag in ("mailing", "mailed") if flag in flags)
    return "<!-- automation-digest run=%s open=%s%s -->" % (run, items, extra)


def with_marker(body, state, flags):
    """body with its last marker rewritten to carry flags; the visible text is unchanged."""
    new = marker(state["run"], state["open"], flags)
    spans = list(MARK.finditer(body))
    return body[:spans[-1].start()] + new + body[spans[-1].end():] if spans else body.rstrip("\n") + "\n" + new + "\n"


def order(run):
    """Run ids grow over time; none and local count as oldest."""
    return int(run) if run and run.isdigit() else -1


def is_bot(login):
    return login in BOTS


def digest_issue():
    """(number, body) of the oldest digest issue with a marker, a bot-authored one first (an issue a person made, by
    --live or before this check, is still used when no bot one exists); (None, "") when none; None when gh fails."""
    done = gh("issue", "list", "--label", "automation", "--state", "all", "--limit", "300", "--json", "number,title,body,author")
    if done.returncode:
        return None
    hits = [item for item in loads(done, []) if item.get("title") == TITLE and parse(item.get("body"))]
    hits.sort(key=lambda item: (not is_bot((item.get("author") or {}).get("login")), item["number"]))
    return (hits[0]["number"], hits[0]["body"]) if hits else (None, "")


def stamp(text):
    """A timestamp, or None; gh prints an unfinished job's completedAt as year 1, which is no time at all."""
    try:
        when = datetime.datetime.fromisoformat((text or "").replace("Z", "+00:00"))
    except ValueError:
        return None
    return when if when.year >= 1970 else None


def is_local(run):
    """A run the Mac's tick made: its id is the 12-digit UTC minute YYYYMMDDHHMM, larger than any Actions run id."""
    return bool(re.fullmatch(r"20\d{10}", str(run or "")))


def created(run):
    if not run or not run.isdigit():
        return None
    if is_local(run):
        return datetime.datetime.strptime(run, "%Y%m%d%H%M").replace(tzinfo=datetime.timezone.utc)
    return stamp(gh("run", "view", run, "--json", "createdAt", "-q", ".createdAt").stdout.strip())


def run_comment(number, run):
    """The newest bot comment on issue number whose last marker has run=R: {id, body, url, state}; None when none;
    False when gh can't read. Reads every page since the run started, so an old run's comment is still found."""
    since = created(run)
    path = "repos/{owner}/{repo}/issues/%s/comments?per_page=100" % number
    if since:
        path += "&since=" + (since - datetime.timedelta(minutes=5)).strftime("%Y-%m-%dT%H:%M:%SZ")
    done = gh("api", "--paginate", "--slurp", path)
    if done.returncode:
        return False
    pages = loads(done, [])
    best = None
    for item in [c for page in pages if isinstance(page, list) for c in page]:
        lines = [line for line in (item.get("body") or "").splitlines() if line.strip()]
        state = parse(lines[-1]) if lines else None
        if state and state["run"] == run and is_bot((item.get("user") or {}).get("login")):
            if best is None or (item.get("created_at") or "") >= best["created"]:
                best = {"id": item.get("id"), "body": item.get("body") or "", "url": item.get("html_url") or "",
                        "state": state, "created": item.get("created_at") or ""}
    return best


def save_comment(comment_id, body):
    return gh("api", "-X", "PATCH", "repos/{owner}/{repo}/issues/comments/%s" % comment_id, "-f", "body=" + body).returncode == 0


def milestone_titles():
    """{number: title} of every milestone; None when gh can't read them."""
    done = gh("api", "--paginate", "--slurp", "repos/{owner}/{repo}/milestones?state=all&per_page=100")
    if done.returncode:
        return None
    return {m["number"]: m.get("title") or "" for page in loads(done, []) if isinstance(page, list) for m in page
            if isinstance(m, dict) and isinstance(m.get("number"), int)}


def jobs(run, now):
    """[(seconds, minutes)] per job of run, a running job counted to now; None when gh can't read."""
    done = gh("run", "view", str(run), "--json", "jobs")
    data = loads(done, None)
    if not isinstance(data, dict):
        return None
    out = []
    for job in data.get("jobs") or []:
        start, end = stamp(job.get("startedAt")), stamp(job.get("completedAt"))
        seconds = max(0, int(((end or now) - start).total_seconds())) if start else 0
        out.append((seconds, math.ceil(seconds / 60)))
    return out


def runs(workflow, limit, after=None):
    args = ["run", "list", "--workflow", workflow, "--limit", str(limit), "--json", "databaseId,createdAt,status,url"]
    if after:
        args += ["--created", ">=" + after.strftime("%Y-%m-%dT%H:%M:%SZ")]
    done = gh(*args)
    return None if done.returncode else loads(done, [])


def round_cost(run, previous=None, now=None):
    """The round's job time and spend; a dict with `error` when it couldn't be read."""
    now = now or datetime.datetime.now(datetime.timezone.utc)
    if not run or not str(run).isdigit():
        return {"error": "no run id"}
    if is_local(run):
        return {"local": max(0, int((now - created(str(run))).total_seconds())), "seconds": 0}
    start = created(str(run))
    health = jobs(run, now)
    if start is None or health is None:
        return {"error": "gh couldn't read run %s" % run}
    listed = runs("regression.yml", REG_LOOKBACK)
    if listed is None:
        return {"error": "gh couldn't list the regression runs"}
    own = [r for r in listed if stamp(r.get("createdAt")) and start - WINDOW <= stamp(r["createdAt"]) < start]
    own.sort(key=lambda r: r["createdAt"])
    reg = own[-1] if own else None
    reg_jobs = jobs(reg["databaseId"], now) if reg else []
    if reg_jobs is None:
        return {"error": "gh couldn't read regression run %s" % reg["databaseId"]}
    cost = {"health": sum(s for s, _ in health), "regression": sum(s for s, _ in reg_jobs) if reg else None,
            "running": bool(reg) and reg.get("status") != "completed", "reg_url": reg.get("url") if reg else "",
            "budget": BUDGET_MINUTES, "note": ""}
    cost["seconds"] = cost["health"] + (cost["regression"] or 0)
    cost["over"] = cost["seconds"] > BUDGET_MINUTES * 60
    cost["minutes"], cost["first"] = spend(run, reg, health, reg_jobs, previous, now, cost)
    return cost


def spend(run, reg, health, reg_jobs, previous, now, cost):
    """(minutes, first): minutes of every run started since the previous round's health run, or of this round's own two
    runs when that run can't be read."""
    after = created(previous) if previous and previous != str(run) else None
    own = sum(m for _, m in health) + sum(m for _, m in reg_jobs)
    if after is None:
        return own, True
    total, read, unread, notes = 0, 0, 0, []
    for workflow in ("regression.yml",):
        listed = runs(workflow, RUN_LIMIT, after)
        if listed is None:
            return own, True
        if len(listed) >= RUN_LIMIT:
            notes.append("NOTE: more than %d runs since the last round; the spend is a lower bound" % RUN_LIMIT)
        for item in listed:
            when = stamp(item.get("createdAt"))
            if when is None or when <= after or str(item.get("databaseId")) == str(previous):
                continue
            counted = jobs(item["databaseId"], now) if read < JOB_READS else None
            read += 1
            unread += counted is None
            total += sum(m for _, m in counted or [])
    if unread:
        notes.append("NOTE: %d runs since the last round weren't read; the spend is a lower bound" % unread)
    cost["note"] = "; ".join(notes)
    return total, False


def minutes(seconds):
    return int(round(seconds / 60.0))


def line(cost):
    if cost and cost.get("local") is not None:
        return "local run, %d min, 0 Actions minutes (health runs on the Mac)" % minutes(cost["local"])
    if not cost or cost.get("error"):
        return "not read (%s) (ROUND_UNREAD)" % ((cost or {}).get("error") or "no data")
    if cost["regression"] is None:
        reg = "regression: no run found"
    elif cost["running"]:
        reg = "regression still running, partial %d min" % minutes(cost["regression"])
    else:
        reg = "regression %d min" % minutes(cost["regression"])
    text = "round %d min of job time (%s, health %d min so far, through the digest); %d Actions minutes of runs started " \
           "since the last round%s" % (minutes(cost["seconds"]), reg, minutes(cost["health"]), cost["minutes"],
                                        " (first round counted)" if cost["first"] else "")
    if cost["over"]:
        text = "OVER %d min: slow a routine down or turn it off. %s" % (cost["budget"], text)
    return text + ("; " + cost["note"] if cost["note"] else "")


def fetch_suite_time(tree, env, log, child):
    """The newest suite-time artifact of regression.yml into the git common dir, marked ci (the old health job's step)."""
    ids = re.findall(r"\d+", child(["gh", "run", "list", "--workflow", "regression.yml", "--limit", "20", "--json", "databaseId", "-q", ".[].databaseId"], tree, env, 30, log)[1])
    into = tempfile.mkdtemp()
    try:
        for number in ids:
            got = child(["gh", "run", "download", number, "--pattern", "suite-time*", "--dir", into], tree, env, 60, log)[0] == 0
            files = glob.glob(into + "/suite-time.tsv") + glob.glob(into + "/*/suite-time.tsv")  # one per shard, or the old single artifact
            if got and files:
                rows = [c[:4] + ["ci"] for f in files for c in (r.split("\t") for r in open(f).read().splitlines()) if len(c) >= 4 and c[1] == "full" and c[2].isdigit()]
                rows = sorted(rows, key=lambda c: int(c[2]))[-1:]  # the shards run side by side: the suite took as long as the slowest
                where = os.path.join(tree, subprocess.run(["git", "rev-parse", "--git-common-dir"], cwd=tree, capture_output=True, text=True).stdout.strip(), "loop")
                os.makedirs(where, exist_ok=True)
                open(os.path.join(where, "suite-times.tsv"), "a").write("".join("\t".join(r) + "\n" for r in rows))
                return "SUITE_TIME: the newest regression run's full-suite time is in " + where
    finally:
        shutil.rmtree(into, ignore_errors=True)
    return "NOTE: no suite-time artifact from the regression workflow yet; health shows the full-suite time as unknown"


def summary(text):
    path = os.environ.get("GITHUB_STEP_SUMMARY")
    if path:
        try:
            with open(path, "a") as handle:
                handle.write(text.rstrip("\n") + "\n")
        except OSError:
            pass


# The round's mail from its digest comment: subject, plain text and a small escaped HTML part (mail.py sends it).
# Links become anchors only for https://github.com/ URLs; everything else is escaped text.

def inline(text):
    out = []
    for piece in re.split(r"(\[[^\]]*\]\([^)\s]*\))", text):
        link = re.fullmatch(r"\[([^\]]*)\]\(([^)\s]*)\)", piece)
        if link and link.group(2).startswith("https://github.com/"):
            out.append('<a href="%s">%s</a>' % (html.escape(link.group(2), quote=True), html.escape(link.group(1))))
        elif link:
            out.append(html.escape(link.group(1) + " (" + link.group(2) + ")"))
        else:
            out.append(html.escape(piece))
    joined = "".join(out)
    joined = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", joined)
    return re.sub(r"`([^`]+)`", r"<code>\1</code>", joined).replace("**", "")


def to_html(text):
    out, table, items = [], [], []

    def flush():
        if table:
            out.append("<table>" + "".join("<tr>%s</tr>" % "".join("<td>%s</td>" % inline(c.strip()) for c in row)
                                           for row in table) + "</table>")
            table.clear()
        if items:
            out.append("<ul>" + "".join("<li>%s</li>" % inline(i) for i in items) + "</ul>")
            items.clear()
    for line in text.splitlines():
        if line.startswith("|"):
            cells = [c.replace("\\|", "|") for c in re.split(r"(?<!\\)\|", line.strip().strip("|"))]
            if not all(re.fullmatch(r"\s*-+\s*", c) for c in cells):
                table.append(cells)
            continue
        if line.startswith("- "):
            items.append(line[2:])
            continue
        flush()
        if line.startswith("### "):
            out.append("<h3>%s</h3>" % inline(line[4:]))
        elif line.strip():
            out.append("<p>%s</p>" % inline(line))
    flush()
    return "<html><body>%s</body></html>" % "\n".join(out)


def message(body, repo):
    lines = [line for line in body.splitlines() if not MARK.search(line)]
    if lines:
        lines[0] = re.sub(r"^@[A-Za-z0-9-]+ ", "", lines[0])
    text = "\n".join(lines).strip() + "\n"
    counts = {"New": 0, "Still open": 0, "Fixed": 0}
    for kind, n in re.findall(r"^\*\*(New|Still open|Fixed)\*\* \((\d+)\)", text, re.M):
        counts[kind] += int(n)
    subject = "Automation digest: %d new, %d still open, %d fixed (%s)" % (counts["New"], counts["Still open"], counts["Fixed"], repo)
    return subject, text, to_html(text)


# The schedule on a machine with no launch agent (a Windows PC): `local register`, and the mail file.
def mail_path(home):
    return os.environ.get("LOOP_MAIL_ENV") or os.path.join(home, "mail.env")


def mail_mode(path):
    return "MAIL_ENV_MODE" if os.name != "nt" and os.stat(path).st_mode & 0o077 else ""


def register_repo(w, root, cfg):
    cron = cfg.get("health_cron") or "47 */4 * * *"
    if cron != "off" and not w.slots(cron):
        sys.exit("REFUSED: health_cron %s is not an every-N-hours or fixed-hours shape. Fix: edit .loop/config.json (SCHEDULE_CRON)" % cron)
    origin = w.origin_of(root)
    if not origin:
        sys.exit("REFUSED: this repo has no origin remote (SCHEDULE_NO_ORIGIN)")
    key, path = w.key_of(origin), os.path.realpath(root)
    os.makedirs(os.path.join(w.home(), "log"), 0o700, exist_ok=True)
    with w.locked("registry", 10):
        data = w.load()
        other = data["repos"].get(key, {}).get("path", path)
        if os.path.realpath(other) != path and os.path.isdir(other):
            sys.exit("REFUSED: %s is already registered for this origin; run local uninstall there first (SCHEDULE_DUPLICATE_ORIGIN)" % other)
        data["repos"] = {k: e for k, e in data["repos"].items() if e["path"] != path or k == key}
        data["repos"].setdefault(key, {}).update(path=path, origin=origin, cron=cron, name=w.task_name(root))
        w.save(data)
    print("SCHEDULE registered %s (%d repos) in %s; no launch agent written. Next: automation.py local tick --dry-run" % (key, len(data["repos"]), w.home()))
    return 0
