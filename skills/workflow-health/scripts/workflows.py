"""The local schedule: one user launch agent that fires `tick`, a registry of repos kept outside every repo, and the tick:
health and the judge (the owner's own claude login) for every repo, the full regression for a private repo, the digest, the mail.
launchd runs one coalesced fire at wake, so a run missed while the Mac slept happens at the next wake. Nothing goes in a repo.
"""
import contextlib
import datetime
import hashlib
import json
import os
import plistlib
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time

import register
import rounds

LABEL = "com.workflow-loop.schedule"
GROUPS = "requirements,traceability,consistency,docs,freshness,tests,performance,security,size,hygiene,adoption"
MAIL_SECRETS = ("DIGEST_TO", "DIGEST_FROM", "CLOUDFLARE_ACCOUNT_ID", "CLOUDFLARE_EMAIL_TOKEN", "DIGEST_SMTP_USER", "DIGEST_SMTP_PASSWORD")
HERE = os.path.dirname(os.path.abspath(__file__))
STAMP = "%Y-%m-%dT%H:%M:%SZ"
UID = "gui/%d" % getattr(os, "getuid", lambda: 0)()
TASK, MAX_HOURS = "%s-health-regression", 4  # the one local task per repo, and the longest gap between its runs


def alive(pid):
    """Raises ProcessLookupError when pid is gone; on Windows asks tasklist, as a signal probe would send Ctrl+C."""
    if os.name == "nt":
        if str(pid).encode() not in subprocess.run(["tasklist", "/FI", "PID eq %d" % pid, "/NH"], capture_output=True).stdout.split():
            raise ProcessLookupError(pid)
    else:
        os.kill(pid, 0)  # posix-only branch


def stop(pid):
    """Kill a child started with start_new_session=True and everything it started."""
    if os.name == "nt":
        subprocess.run(["taskkill", "/T", "/F", "/PID", str(pid)], capture_output=True)
    else:
        os.killpg(pid, signal.SIGKILL)  # posix-only branch


def home():
    return os.environ.get("LOOP_SCHEDULE_HOME") or os.path.expanduser("~/.workflow-loop/schedule")


def plist_path():
    return os.path.join(os.environ.get("LOOP_AGENTS_DIR") or os.path.expanduser("~/Library/LaunchAgents"), LABEL + ".plist")


def program():
    return os.environ.get("LOOP_SCHEDULE_PROGRAM") or os.path.join(HERE, "automation.py")


def launchctl(*args):
    try:
        return subprocess.run([os.environ.get("LOOP_LAUNCHCTL") or "launchctl", *args], capture_output=True, text=True, timeout=30).returncode
    except (OSError, subprocess.TimeoutExpired):
        return 1


def scrub(text):
    return re.sub(r"(gh[pousr]_|github_pat_|sk-ant-)\w+|Bearer \S+|//[^/\s:@]+:[^/\s@]+@", "<x>", text or "")


def now():
    return datetime.datetime.now(datetime.timezone.utc)


def when(text):
    try:
        return datetime.datetime.strptime(text, STAMP).replace(tzinfo=datetime.timezone.utc)
    except (TypeError, ValueError):
        return None


def load():
    path = os.path.join(home(), "repos.json")
    try:
        data = json.load(open(path)) if os.path.exists(path) else {"repos": {}}
        assert isinstance(data["repos"], dict)
        return data
    except (OSError, ValueError, KeyError, AssertionError):
        sys.exit("REGISTRY_UNREADABLE %s: fix or remove it (REGISTRY_UNREADABLE)" % path)


def save(data):
    path = os.path.join(home(), "repos.json")
    os.makedirs(home(), 0o700, exist_ok=True)
    with os.fdopen(os.open(path + ".tmp", os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600), "w") as handle:
        json.dump(data, handle, indent=1)
    os.replace(path + ".tmp", path)


@contextlib.contextmanager
def locked(name, wait=0):
    """Yield None, or the pid holding this mkdir lock; a lock whose pid is dead is taken over."""
    os.makedirs(home(), 0o700, exist_ok=True)
    path, holder = os.path.join(home(), name + ".lock"), 0
    for _ in range(wait * 10 + 2):
        try:
            os.mkdir(path)
            open(os.path.join(path, "pid"), "w").write(str(os.getpid()))
            break
        except FileExistsError:
            try:
                holder = int(open(os.path.join(path, "pid")).read())
                alive(holder)
                time.sleep(0.1)
            except (OSError, ValueError):
                shutil.rmtree(path, ignore_errors=True)
    else:
        yield holder
        return
    try:
        yield None
    finally:
        shutil.rmtree(path, ignore_errors=True)


def key_of(origin):
    """12 hex of host/owner/repo: the ssh, https and .git forms of one repository give one key."""
    text = re.sub(r"^[^@/]+@", "", re.sub(r"^[a-z+]+://", "", origin.strip()))
    colon = text.find(":")
    text = text[:colon] + "/" + text[colon + 1:] if 0 <= colon < (text.find("/") if "/" in text else len(text)) else text
    return hashlib.sha1(re.sub(r"(\.git)?/*$", "", text).lower().encode()).hexdigest()[:12]


def slots(cron):
    """([(hour, minute)], hours between runs) for `M */N * * *` or `M h[,h] * * *`; None for any other shape."""
    got = re.fullmatch(r"(\d{1,2}) (?:\*/(\d{1,2})|(\d{1,2}(?:,\d{1,2})*)) \* \* \*", cron or "")
    if not got or int(got.group(1)) > 59:
        return None
    minute, step = int(got.group(1)), int(got.group(2) or 0)
    if got.group(2):
        return ([(h, minute) for h in range(0, 24, step)], step) if step and 24 % step == 0 else None
    hours = sorted({int(h) for h in got.group(3).split(",")})
    return ([(h, minute) for h in hours], max((b - a) % 24 or 24 for a, b in zip(hours, hours[1:] + hours[:1]))) if hours[-1] < 24 else None


def plist_text(prog, merged, dirs):
    log = os.path.join(home(), "log", "tick.log")
    return plistlib.dumps({"Label": LABEL, "ProgramArguments": [shutil.which("python3") or "/usr/bin/python3", prog, "local", "tick", "--scheduled"],
                           "StartCalendarInterval": [{"Hour": h, "Minute": m} for h, m in merged], "RunAtLoad": False, "ProcessType": "Background",
                           "EnvironmentVariables": {"PATH": ":".join(dirs + ["/usr/bin", "/bin"])}, "StandardOutPath": log, "StandardErrorPath": log}).decode()


def agent_text(data):
    merged = sorted({s for e in data["repos"].values() if slots(e.get("cron")) for s in slots(e["cron"])[0]})
    return plist_text(program(), merged, list(dict.fromkeys(os.path.dirname(p) for p in (shutil.which("gh"), shutil.which("claude")) if p)))


def write_agent(data):
    """Write the agent for the repos left (or remove it with the last); True when its text changed."""
    if not data["repos"]:
        launchctl("bootout", UID + "/" + LABEL)
        return os.path.exists(plist_path()) and not os.remove(plist_path())
    text = agent_text(data)
    if os.path.exists(plist_path()) and open(plist_path()).read() == text:
        return False
    os.makedirs(os.path.dirname(plist_path()), exist_ok=True)
    open(plist_path(), "w").write(text)
    return True


def origin_of(root):
    done = subprocess.run(["git", "remote", "get-url", "origin"], cwd=root, capture_output=True, text=True)
    return done.stdout.strip() if done.returncode == 0 else ""


def task_name(root):
    """The repo's one local task: <repo name from its origin>-health-regression."""
    return TASK % (re.split(r"[/:]", re.sub(r"(\.git)?/*$", "", origin_of(root)))[-1] or os.path.basename(os.path.realpath(root)))


def due(entry, interval, at):
    last = when(entry.get("last_run"))
    return last is None or (at - last).total_seconds() >= (interval - min(1, interval / 2)) * 3600


def install(root, cfg, load_it=False):
    cron, real = cfg.get("health_cron") or "47 */4 * * *", os.path.realpath(program())
    if (os.environ.get("LOOP_SCHEDULE_PLATFORM") or sys.platform) != "darwin":
        sys.exit("REFUSED: the launch agent is for macOS; plist, status and tick still work (SCHEDULE_PLATFORM)")
    if cron != "off" and not slots(cron):
        sys.exit("REFUSED: health_cron %s is not an every-N-hours or fixed-hours shape. Fix: edit .loop/config.json (SCHEDULE_CRON)" % cron)
    if not os.environ.get("LOOP_SCHEDULE_PROGRAM") and ("/loop/worktrees/" in real or real.startswith((os.path.realpath(tempfile.gettempdir()), os.sep + "private" + os.sep + "tmp"))):
        sys.exit("REFUSED: run install from the installed skills or the repo's main checkout (SCHEDULE_PROGRAM_PATH)")
    origin = origin_of(root)
    if not origin:
        sys.exit("REFUSED: this repo has no origin remote (SCHEDULE_NO_ORIGIN)")
    key, path = key_of(origin), os.path.realpath(root)
    os.makedirs(os.path.join(home(), "log"), 0o700, exist_ok=True)  # launchd opens the agent's log file before the first tick
    with locked("registry", 10):
        data = load()
        other = data["repos"].get(key, {}).get("path", path)
        if os.path.realpath(other) != path and os.path.isdir(other):
            sys.exit("REFUSED: %s is already registered for this origin; run local uninstall there first (SCHEDULE_DUPLICATE_ORIGIN)" % other)
        data["repos"] = {k: e for k, e in data["repos"].items() if e["path"] != path or k == key}
        data["repos"].setdefault(key, {}).update(path=path, origin=origin, cron=cron, name=task_name(root))
        loaded, changed = launchctl("print", UID + "/" + LABEL) == 0, write_agent(data)
        save(data)
    boot = ["bootstrap", UID, plist_path()]
    print("SCHEDULE installed for %s (%d repos)" % (key, len(data["repos"])))
    if load_it:
        launchctl(*boot)
    print("%s: launchctl %s\nStop it: launchctl bootout %s/%s" % ("LOADED" if load_it else "Load it", " ".join(boot), UID, LABEL))
    print("RELOAD: bootout then bootstrap" * (loaded and changed) or "Next: automation.py local status; local tick --dry-run")
    return 0


def uninstall(root):
    with locked("registry", 10):
        data = load()
        data["repos"] = {k: e for k, e in data["repos"].items() if e["path"] != os.path.realpath(root)}
        os.name == "nt" or write_agent(data)  # a Windows PC has no launch agent
        save(data)
    print("SCHEDULE removed here (%d repos left)%s" % (len(data["repos"]), "; NOTE: the agent stays loaded for them" * bool(data["repos"])))
    return 0


def child(argv, cwd, env, seconds, log):
    """(exit code, scrubbed output); the child runs in its own process group and a timeout kills the whole group."""
    with tempfile.TemporaryFile("w+") as out:
        try:
            run = subprocess.Popen(argv, cwd=cwd, env=env, stdout=out, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, start_new_session=True)
            code = run.wait(timeout=max(1, seconds))
        except OSError as error:
            return 127, str(error)
        except subprocess.TimeoutExpired:
            stop(run.pid)
            run.wait()
            code = 124
        out.seek(0)
        text = scrub(out.read())
    log.write(text + "\n" * (not text.endswith("\n")))
    return code, text


REGRESSION_WAIT = 20 * 60  # at most this long for a running regression to end before health goes on without it (AUT-7: 30 + 15)


def wait_regression(path, env, log, finish):
    """WAITED when the newest regression.yml run was in progress and ended, else the state it found; never past `finish`."""
    began = time.time()
    while True:
        done = child(["gh", "run", "list", "--workflow", "regression.yml", "--limit", "1", "--json", "status"], path, env, 30, log)
        try:
            status = (json.loads(done[1])[0] or {}).get("status")
        except (ValueError, IndexError, TypeError):
            return "REGRESSION_WAIT: no regression run found, health goes on"
        if status in (None, "completed"):
            return "REGRESSION_WAIT: regression has finished" + (" after %d s" % (time.time() - began) if time.time() - began > 1 else "")
        if time.time() - began > REGRESSION_WAIT or time.time() + 60 > finish:
            return "REGRESSION_WAIT: regression still %s after %d s, health goes on without it" % (status, time.time() - began)
        time.sleep(60)


def tick_repo(key, entry, begin, finish):
    """One repo's tick: True when every step ran, False when a step did not, None when it was skipped."""
    path, log, py, env = entry["path"], open(os.path.join(home(), "log", "tick.log"), "a"), sys.executable, dict(os.environ)
    say = lambda text: (print(text), log.write(text + "\n"))  # noqa: E731
    for argv, code, fix in ((["gh", "auth", "status"], "SCHEDULE_AUTH", "gh auth login"), (["gh", "api", "rate_limit"], "SCHEDULE_OFFLINE", "check the network")):
        if child(argv, path, env, 20, log)[0]:
            say("SKIPPED %s (%s failed) Fix: %s (%s)" % (key, " ".join(argv[:3]), fix, code))
            entry["skips"], entry["cause"] = entry.get("skips", 0) + 1, code
            return None
    conf = json.load(open(os.path.join(path, ".loop", "config.json"))) if os.path.exists(os.path.join(path, ".loop", "config.json")) else {}
    base, tree = conf.get("base") or "main", os.path.join(home(), key, "tree")
    if not re.fullmatch(r"\w[\w./-]*", str(base)):  # a base is a branch name, never an option for git fetch
        say("SKIPPED %s (base %r is not a branch name) (SCHEDULE_BASE)" % (key, base))
        return False
    os.makedirs(os.path.dirname(tree), exist_ok=True)
    child(["git", "worktree", "prune"], path, env, 30, log)
    if child(["git", "fetch", "origin", base], path, env, 60, log)[0] or child(
            ["git", "-C", tree, "checkout", "--detach", "-f", "origin/" + base] if os.path.isdir(tree) else ["git", "worktree", "add", "--detach", tree, "origin/" + base],
            path, env, 60, log)[0]:
        say("SKIPPED %s (could not check out origin/%s) (SCHEDULE_OFFLINE)" % (key, base))
        return False
    child(["git", "-C", tree, "clean", "-fdxq"], path, env, 60, log)
    own = os.path.join(tree, "skills")
    skills = own if os.path.exists(os.path.join(own, "workflow-health", "scripts", "health.py")) else os.path.dirname(os.path.dirname(HERE))
    say("SKILLS: " + ("checkout" if skills == own else "installed"))
    for name in ("ANTHROPIC_API_KEY", "CLAUDECODE"):
        env.pop(name, None)
    secrets, note, mail = {}, "MAIL_NOT_SET_UP", register.mail_path(home())
    if os.path.exists(mail):
        note = register.mail_mode(mail)
        for row in [] if note else open(mail):
            name, _, value = row.strip().partition("=")
            secrets.update({name: value} if name in MAIL_SECRETS else {})
    has = lambda *names: str(all(secrets.get(n) for n in names)).lower()  # noqa: E731
    report = os.path.join(home(), key, "health-report.txt")
    env.update(DIGEST_RUN=begin.strftime("%Y%m%d%H%M"), HEALTH_REPORT=report, DIGEST_LAST=entry.get("last_run") or "", DIGEST_MAIL_NOTE=note,
               DIGEST_INTERVAL=str((slots(entry.get("cron")) or (0, 24))[1]), MAIL_ADDR_SET=has("DIGEST_TO", "DIGEST_FROM"),
               MAIL_CF_SET=has("CLOUDFLARE_ACCOUNT_ID", "CLOUDFLARE_EMAIL_TOKEN"), MAIL_SMTP_SET=has("DIGEST_SMTP_USER", "DIGEST_SMTP_PASSWORD"))
    cfg = json.load(open(os.path.join(tree, ".loop", "config.json"))) if os.path.exists(os.path.join(tree, ".loop", "config.json")) else {}
    ok, script = True, lambda skill, name: [py, os.path.join(skills, skill, "scripts", name)]  # noqa: E731

    def step(name, argv, floor=0, extra=None):
        seconds = max(finish - time.time(), floor)
        if seconds <= 0:
            say("SKIPPED %s (cap reached)" % name)
            return None
        return child(argv, tree, dict(env, **(extra or {})), seconds, log)

    if conf.get("regression_runs") == "actions" and conf.get("regression_cron") != "off":
        say(wait_regression(path, env, log, finish))  # health follows the regression run's end, not a fixed offset after its start
    got = step("health check", script("workflow-health", "health.py") + ["check"], extra={"LOOP_MIGRATION_ONLINE": "1"})
    open(report, "w").write(got[1] if got else "")
    ok &= got is not None and step("health file", script("workflow-health", "health.py") + ["file", "--group", GROUPS]) is not None
    got = step("judge", script("workflow-health", "health.py") + ["review"])
    entry["judge_skipped"] = entry.get("judge_skipped", 0) + 1 if got and "JUDGE UNAVAILABLE" in got[1] else 0
    say("JUDGE: " + ("skipped" if entry["judge_skipped"] else "ran" if got else "not run (cap reached)"))
    env["DIGEST_JUDGE"] = "JUDGE_SKIPPED %d ticks in a row (JUDGE_SKIPPED)" % entry["judge_skipped"] * (entry["judge_skipped"] >= 3)
    seen = child(script("workflow-delivery", "private.py") + ["visibility"], tree, env, 30, log)[1].split()[-1:] or ["unknown"]
    setting = cfg.get("regression_runs")
    private = setting == "mac" if setting else seen[0] == "private"
    if setting != "mac" and setting and seen[0] in ("private", "public") and (seen[0] == "private") != private:
        env["DIGEST_DRIFT"] = "DRIFT: regression_runs says %s but the repo is %s; run setup (DRIFT)" % (setting, seen[0])
    say(env.get("DIGEST_DRIFT") or "REGRESSION: runs %s%s" % ("on the Mac" if private else "in GitHub Actions", "" if setting else "; NOTE: regression_runs unset; run setup to record it"))
    if private and cfg.get("regression_cron") != "off":
        got = step("regression", script("workflow-regression", "regression.py") + ["run", cfg.get("ci_levels") or "nightly", "--live", "--timeout", "900"])
        env["DIGEST_REGRESSION"] = ((re.findall(r"^RESULT .*$", got[1], re.M) or ["no RESULT line"])[-1] + ", local run") if got else "skipped (cap reached)"
        ok &= got is not None
    elif not private:
        say(rounds.fetch_suite_time(tree, env, log, child))
    ok &= bool(step("digest", script("workflow-health", "automation.py") + ["digest", "--live"], 120)[0] == 0)
    if secrets:
        ok &= step("mail", script("workflow-health", "mail.py") + ["send"], extra=secrets) is not None
    return ok


def tick(scheduled=False, dry=False, only=""):
    data, begin, status = load(), now(), 0
    total = begin.timestamp() + float(os.environ.get("LOOP_TICK_TOTAL_MINUTES") or 180) * 60
    cap, logfile = float(os.environ.get("LOOP_TICK_MINUTES") or 60) * 60, os.path.join(home(), "log", "tick.log")
    os.makedirs(os.path.dirname(logfile), 0o700, exist_ok=True)
    if not dry and os.path.exists(logfile) and os.path.getsize(logfile) > 200 * 1024:
        open(logfile, "wb").write(open(logfile, "rb").read()[-200 * 1024:])
    for key, entry in sorted(data["repos"].items(), key=lambda kv: kv[1].get("last_run") or ""):
        sl = slots(entry.get("cron"))
        if only and os.path.realpath(only) != os.path.realpath(entry["path"]):
            continue
        if not os.path.isdir(entry["path"]) or not sl or scheduled and not due(entry, sl[1], begin):
            print(("MISSING %s: %s is gone; skipped (PATH_MISSING)" % (key, entry["path"])) if not os.path.isdir(entry["path"]) else
                  "OFF %s: health_cron is off" % key if not sl else "NOT DUE %s (last run %s)" % (key, entry.get("last_run")))
        elif dry:
            print("PLAN %s: %s; due %s; steps: probe, checkout, health, judge, regression or suite time, digest, mail" % (key, entry["path"], due(entry, sl[1], begin)))
        else:
            with locked(key) as holder:
                if holder is not None:
                    print("SKIPPED %s (locked by pid %s)" % (key, holder))
                    continue
                started = time.time()
                try:
                    result = tick_repo(key, entry, begin, min(started + cap, total))
                except Exception as error:  # noqa: BLE001 - the next repo still runs
                    import traceback
                    trace = os.path.join(home(), "log", "trace-%s.txt" % key)
                    open(trace, "w").write(scrub(traceback.format_exc()))
                    print("TICK_CRASH %s: %s; trace %s. Fix: run local tick --repo %s by hand (TICK_CRASH)" % (key, type(error).__name__, trace, entry["path"]))
                    result, status = False, 1
                if result is None:
                    status = status or (0 if scheduled else 3)
                else:
                    entry.update(last_run=begin.strftime(STAMP), last_ok=bool(result), skips=0, seconds=int(time.time() - started))
            with locked("registry", 10):
                fresh = load()
                fresh["repos"][key] = dict(fresh["repos"].get(key, {}), **entry)
                save(fresh)
    return status
