"""Test-local gh: the release PR, the rules endpoint and releases. Everything else goes to dev/toy/fakegh."""
import json, os, subprocess, sys, tempfile
d, a = os.environ["FAKE_GH_DIR"], sys.argv[1:]
def log(): open(os.path.join(d, "calls.log"), "a").write(" ".join(a) + "\n")
def flag(n): return a[a.index(n) + 1] if n in a else None
def load(n):
    try: return json.load(open(os.path.join(d, n)))
    except (OSError, ValueError): return {} if n == "rpr.json" else []
def save(n, v): json.dump(v, open(os.path.join(d, n), "w"))
def out(v): print(json.dumps(v)); sys.exit(0)
def real(): os.execvp(os.environ["TOY_FAKEGH"], [os.environ["TOY_FAKEGH"]] + a)
if a[:1] == ["api"] and "/rules/branches/" in a[1]:
    log()
    if os.path.exists(os.path.join(d, "rules.json")): print(open(os.path.join(d, "rules.json")).read()); sys.exit(0)
    sys.exit(print("gh: Not Found (HTTP 404)", file=sys.stderr) or 1)
prs = load("rpr.json")
if a[:2] == ["pr", "create"] and (flag("--head") or "").startswith("release/"):
    log(); n = str(101 + len(prs))
    prs[n] = {"number": int(n), "url": "https://example.test/pull/" + n, "head": flag("--head"), "title": flag("--title"),
              "body": flag("--body"), "state": "OPEN", "mergeStateStatus": "CLEAN", "reviewDecision": "", "statusCheckRollup": []}
    save("rpr.json", prs); print(prs[n]["url"]); sys.exit(0)
if a[:1] == ["pr"] and len(a) > 2 and a[1] in ("view", "merge", "close"):
    key = a[2].rstrip("/").split("/")[-1]
    pr = prs.get(key) or next((p for p in prs.values() if p["head"] == a[2] and p["state"] == "OPEN"), None)
    if not pr:
        if a[1] == "merge": os.environ["TOY_SERVER_MERGE"] = "1"
        real()
    log()
    if a[1] == "view": out({k: pr.get(k) for k in ("state", "mergeStateStatus", "reviewDecision", "mergeCommit", "statusCheckRollup", "url", "number")})
    if a[1] == "close": pr["state"] = "CLOSED"
    elif "--admin" in a: sys.exit("no --admin in a test")
    else:
        mode = os.environ.get("TOY_PR_MODE", "ok")
        if mode == "review": pr.update(mergeStateStatus="BLOCKED", reviewDecision="REVIEW_REQUIRED")
        elif mode == "pending": pr.update(mergeStateStatus="BLOCKED", statusCheckRollup=[{"status": "IN_PROGRESS"}])
        elif mode == "dirty" and not os.path.exists(os.path.join(d, "dirtied")):  # only the first release PR conflicts
            open(os.path.join(d, "dirtied"), "w").close(); pr.update(mergeStateStatus="DIRTY")
        elif mode == "mismatch":  # merged at a commit whose VERSION is not the release's
            old = subprocess.run(["git", "--git-dir", os.environ["FAKE_GH_ORIGIN"], "rev-parse", "main"], capture_output=True, text=True).stdout.strip()
            pr.update(state="MERGED", mergeCommit={"oid": old})
        else:
            t = tempfile.mkdtemp(); env = dict(os.environ, TOY_SERVER_MERGE="1")
            sh = lambda *c: subprocess.run(list(c), cwd=t, env=env, capture_output=True, text=True, check=True).stdout.strip()
            sh("git", "clone", "-q", os.environ["FAKE_GH_ORIGIN"], ".")
            sh("git", "-c", "user.email=t@example.test", "-c", "user.name=Toy", "merge", "-q", "--no-ff", "--no-edit", "origin/" + pr["head"])
            sh("git", "push", "-q", "origin", "HEAD:main")
            pr.update(state="MERGED", mergeCommit={"oid": sh("git", "rev-parse", "HEAD")})
    save("rpr.json", prs)
    sys.exit(0 if pr["state"] != "OPEN" else print("merge blocked", file=sys.stderr) or 1)
if a[:2] == ["release", "create"]:
    log(); rel = load("releases.json"); rel.append({"tag": a[2], "target": flag("--target")}); save("releases.json", rel)
    if os.environ.get("TOY_CRASH_CREATE") and not os.path.exists(os.path.join(d, "crashed")):
        open(os.path.join(d, "crashed"), "w").close(); sys.exit("connection reset after create")
    print("https://example.test/releases/" + a[2]); sys.exit(0)
if a[:2] == ["release", "view"]:
    log(); found = [r for r in load("releases.json") if r["tag"] == a[2]]
    if found: out({"targetCommitish": found[0]["target"], "url": "https://example.test/releases/" + a[2]})
    sys.exit(print("release not found", file=sys.stderr) or 1)
real()
