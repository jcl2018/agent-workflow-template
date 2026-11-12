"""What the health commands read from gh and from the pages. A milestone is optional and free form: nothing here requires one.

It holds the cached list of every issue (fetch), the feature a finding is about (feature_of, from .loop/docs.tsv) and the
feature an issue is about (feature_group: its feature:<Page> label, else a milestone named like a page, else No feature),
an issue's marker key and evidence hash (key_of, legacy, evidence_of, covering), and triage (listing, close): open
findings per feature, closed in a batch only with the owner's words. Read-only apart from close, which needs --yes.
"""
import datetime
import hashlib
import json
import os
import re
import subprocess
import sys

from defects import defined, table


os.environ.update(GIT_TERMINAL_PROMPT="0", GH_PROMPT_DISABLED="1", GIT_EDITOR="true", GIT_ASKPASS="true", SSH_ASKPASS="true")
if not sys.stdin or not sys.stdin.isatty():
    os.dup2(os.open(os.devnull, os.O_RDONLY), 0)

# No terminal, no waiting: a prompt from git or gh must fail, not block.
os.environ.update(GIT_TERMINAL_PROMPT="0", GH_PROMPT_DISABLED="1", GIT_EDITOR="true", GIT_ASKPASS="true", SSH_ASKPASS="true")

CACHE = {}
FIELDS = ("number", "title", "body", "state", "labels", "milestone", "created_at", "closed_at", "pull_request")


def slim(item):
    out = {key: item.get(key) for key in FIELDS}
    out["labels"] = [label.get("name") if isinstance(label, dict) else str(label) for label in item.get("labels") or []]
    stone = item.get("milestone")
    out["milestone"] = stone.get("title") if isinstance(stone, dict) else stone
    return out


SCOPES = {"health": ["state=open&labels=health"], "open": ["state=open"], "held": ["state=all&labels=health", "state=open"]}
PAGE, MOST_PAGES, PAGE_SECONDS = 100, 200, 60


def in_scope(issue, scope):
    """health: open findings; open: open issues; held: every health issue, any state, and the open issues."""
    opened, health = issue.get("state") == "open", is_health(issue)
    return (opened and health) if scope == "health" else opened if scope == "open" else (opened or health)


def pages_of(root, query):
    """(issues, why): one filtered query read a page of 100 at a time, each page with its own time limit."""
    out = []
    for page in range(1, MOST_PAGES + 1):
        try:
            done = subprocess.run(["gh", "api", "repos/{owner}/{repo}/issues?%s&per_page=%d&page=%d" % (query, PAGE, page)],
                                  cwd=root, capture_output=True, text=True, timeout=PAGE_SECONDS)
        except (OSError, subprocess.SubprocessError) as error:
            return None, "gh not available here (page %d of %s: %s)" % (page, query, str(error)[:80])
        if done.returncode:
            return None, "gh not available here (page %d of %s: %s)" % (
                page, query, (done.stderr.strip().splitlines() or ["exit %d" % done.returncode])[0][:100])
        try:
            got = json.loads(done.stdout or "[]")
            got = got if isinstance(got, list) else [got]
        except ValueError as error:
            return None, "gh gave unreadable output (page %d of %s: %s)" % (page, query, str(error)[:80])
        out += got
        if len(got) < PAGE:
            return out, ""
    return None, "more than %d issues match %s: narrow it" % (PAGE * MOST_PAGES, query)


def fetch(root, scope="open"):
    """(issues or None, why), only the slice a command needs (SCOPES), read in pages. Pull requests are left out."""
    key = (root, scope)
    if key in CACHE:
        return CACHE[key]
    fixture = os.environ.get("LOOP_HEALTH_GH_FIXTURE")
    found, why = [], ""
    if fixture:
        try:
            with open(fixture) as handle:
                found = json.load(handle)
        except (OSError, ValueError, AttributeError) as error:
            found, why = None, "the issue fixture can't be read: %s" % error
    else:
        for query in SCOPES[scope]:
            got, why = pages_of(root, query)
            if got is None:
                found = None
                break
            found += got
    if found is not None:
        try:
            seen = {}
            for item in found:
                one = slim(item)
                if not one.get("pull_request") and in_scope(one, scope):
                    seen[one["number"]] = one
            found = list(seen.values())
        except (AttributeError, TypeError) as error:
            found, why = None, "gh gave unreadable output (%s)" % str(error)[:80]
    CACHE[key] = (found, why)
    return CACHE[key]


def is_health(issue):
    return "health" in (issue.get("labels") or [])


OLD = {"requirements": "criteria", "performance": "cost", "traceability": "criteria", "tests": "criteria"}
OLD_RULE = {"scripts": "limit", "seen-red": "proof", "done": "rows"}


def key_of(item):
    return "%s:%s:%s" % (item["family"], item["subject"], item["rule"])


def legacy(item):
    """The keys an older health wrote for this finding."""
    family, rule = OLD.get(item["family"]), OLD_RULE.get(item["rule"], item["rule"])
    out = ["%s:%s:%s" % (family, item["subject"], rule)] if family else []
    if item["family"] == "size":
        out.append("size:%s:limit" % item["subject"])
    return out


def evidence_of(item):
    """sha8 of the finding's identity and stable citations; never details, ages, counts or sizes (review: normalized)."""
    cites = item.get("evidence") or item["subject"]
    if item["family"] == "review":
        cites = ",".join(sorted({re.sub(r":\d+(-\d+)?$", "", c.strip()) for c in cites.split(",") if c.strip()}))
    return hashlib.sha1(("%s|%s" % (key_of(item), cites)).encode()).hexdigest()[:8]


def title_of(stone):
    """A milestone's title from gh's {"title": ...}, issues.fetch's plain title, or nothing."""
    return (stone.get("title") if isinstance(stone, dict) else stone) or ""


def covering(item, issues):
    """An open non-health issue naming the finding's subject as a whole token."""
    subject = (item.get("evidence") or item["subject"]).split(",")[0].strip()
    if not re.search(r"[/.]|^[A-Z]{2,5}-\d+", subject) or len(subject) < 4:  # a path or an id, never a plain word
        return None
    pattern = re.compile(r"(?<![\w./-])%s(?![\w/-])" % re.escape(subject))
    for issue in issues:
        if issue.get("state") == "open" and not is_health(issue) and \
                pattern.search("%s\n%s" % (issue.get("title") or "", issue.get("body") or "")):
            return issue
    return None


NO_FEATURE = "No feature"
FEATURE_LABELS_DEFAULT = False  # the feature_labels setting (workflow-setup settings.py): off until the owner turns it on
ID = re.compile(r"^[A-Z]{2,5}-\d+[a-z]?$")


def features(root):
    """{page: [paths]} from .loop/docs.tsv, Home left out."""
    out = {}
    try:
        with open(os.path.join(root, ".loop", "docs.tsv")) as handle:
            for line in handle:
                if line.strip() and not line.startswith("#"):
                    page, _, paths = line.rstrip("\n").partition("\t")
                    if page.strip() and page.strip() != "Home":
                        out[page.strip()] = [p.strip().rstrip("/") for p in paths.split(",") if p.strip()]
    except OSError:
        pass
    return out


def by_path(path, pages):
    path = path.split(":")[0].strip()
    if path.startswith("/workflow-"):  # a command: /workflow-docs init is about skills/workflow-docs
        path = "skills/" + path.split()[0].lstrip("/")
    path = path[2:] if path.startswith("./") else path.lstrip("/")
    best, length = None, -1
    for page, paths in pages.items():
        for prefix in paths + ["docs/wiki/%s.md" % page]:
            if (path == prefix or path.startswith(prefix + "/")) and len(prefix) > length:
                best, length = page, len(prefix)
    return best


def feature_label(page):
    """The label that tags an issue with its feature: feature: plus the page name, without commas, newlines or control
    characters, cut on code points at 42 (GitHub allows 50 in all). The one helper for writing and reading it."""
    return "feature:" + "".join(c for c in page if c != "," and c.isprintable())[:42]


def feature_labels_on(root):
    """The feature_labels setting of .loop/config.json: only when true does any code create or apply a feature label."""
    try:
        with open(os.path.join(root, ".loop", "config.json")) as handle:
            value = json.load(handle).get("feature_labels", FEATURE_LABELS_DEFAULT)
    except (OSError, ValueError, AttributeError):
        value = FEATURE_LABELS_DEFAULT
    return value is True


def feature_group(issue, pages):
    """The feature (page name) an issue is about: the page whose feature_label it carries (two pages with one label give
    No feature), else its milestone's title when that is a page's name (an old feature milestone), else No feature. A
    free-form milestone such as v1.0 never makes a feature."""
    names = {str(n).lower() for n in issue.get("labels") or []}
    tagged = [p for p in pages if feature_label(p).lower() in names]
    if tagged:
        return tagged[0] if len(tagged) == 1 else NO_FEATURE
    stone = title_of(issue.get("milestone"))
    return stone if stone in pages else NO_FEATURE


def feature_of(root, item, cache=None):
    """The feature (page name) a finding is about, or None."""
    cache = cache if cache is not None else {}
    pages = cache.setdefault("pages", features(root))
    named = item.get("feature")
    if named:
        return named if named in pages else None
    known = cache.setdefault("ids", defined(root))
    rows = cache.setdefault("rows", {r["id"]: r for r in table(root)})
    for text in (item.get("subject") or "", item.get("evidence") or ""):
        text = text.strip()
        if not text:
            continue
        if ID.match(text) and text in known:
            page = known[text][0]
            return page if page in pages else None
        if text in rows and rows[text]["goal"] in known:
            page = known[rows[text]["goal"]][0]
            return page if page in pages else None
        if text.startswith("#") and text[1:].isdigit():
            found, _ = fetch(root, "open")
            page = next((feature_group(i, pages) for i in found or [] if str(i["number"]) == text[1:]), NO_FEATURE)
            if page != NO_FEATURE:
                return page
            continue
        page = text if text in pages else by_path(text, pages)  # a page-level finding (docs stale) names its page
        if page:
            return page
    return None


# No terminal, no waiting: a prompt from git or gh must fail, not block.
os.environ.update(GIT_TERMINAL_PROMPT="0", GH_PROMPT_DISABLED="1", GIT_EDITOR="true", GIT_ASKPASS="true", SSH_ASKPASS="true")


CAP = 20


def age(issue):
    try:
        when = datetime.date.fromisoformat(str(issue.get("created_at"))[:10])
    except ValueError:
        return 0
    return (datetime.date.today() - when).days


def kind_of(issue):
    tags = [t for t in issue.get("labels") or [] if t.startswith("health:") and t != "health:closed"]
    return tags[0][len("health:"):] if tags else "health"


def open_findings(root, only=None):
    found, why = fetch(root, "health")
    if found is None:
        return None, why
    pages = features(root)
    return [i for i in found if i.get("state") == "open" and is_health(i)
            and (not only or feature_group(i, pages) == only)], ""


def listing(root, only=None):
    found, why = open_findings(root, only)
    if found is None:
        print("REFUSED[gh]: can't list the issues (%s). Nothing was read." % why)
        return 2
    if not found:
        print("TRIAGE: no open findings%s" % (" on " + only if only else ""))
        return 0
    table, pages = {}, features(root)
    for issue in found:
        table.setdefault(feature_group(issue, pages), {}).setdefault(kind_of(issue), []).append(age(issue))
    print("TRIAGE: %d open findings on %d features" % (len(found), len(table)))
    for stone in sorted(table, key=lambda s: (-sum(len(v) for v in table[s].values()), s)):
        print("== %s: %d ==" % (stone, sum(len(v) for v in table[stone].values())))
        for kind, ages in sorted(table[stone].items(), key=lambda kv: (-len(kv[1]), kv[0])):
            print("  %-22s %3d open, oldest %d days, newest %d days" % (kind, len(ages), max(ages), min(ages)))
    return 0


def close(root, kind, why, only=None, older=0, yes=False, most=CAP):
    if not (why or "").strip():
        print("REFUSED[why]: close needs --why with the owner's words. Nothing was closed.")
        return 2
    found, reason = open_findings(root, only)
    if found is None:
        print("REFUSED[gh]: can't list the issues (%s). Nothing was closed." % reason)
        return 2
    match = [i for i in found if kind_of(i) == kind and age(i) >= older]
    if not match:
        print("NOTHING TO CLOSE: no open %s findings%s%s" % (kind, " on " + only if only else "", " %d days or older" % older if older else ""))
        return 0
    pages = features(root)
    for issue in match:
        print("  #%d %s (%d days, %s)" % (issue["number"], issue.get("title") or "", age(issue), feature_group(issue, pages)))
    if len(match) > most:
        print("REFUSED[cap]: %d match, over --max %d. Narrow it with --feature or --older, or raise --max." % (len(match), most))
        return 2
    if not yes:
        print("DRY RUN: %d would close with: %s. To close them, run again with --yes." % (len(match), why))
        return 0
    subprocess.run(["gh", "label", "create", "health:closed", "--description", "Closed in triage by the owner", "--force"],
                   cwd=root, capture_output=True, text=True)
    for issue in match:
        number = str(issue["number"])
        done = subprocess.run(["gh", "issue", "close", number, "--comment", "Closed in triage by the owner: " + why.strip()],
                              cwd=root, capture_output=True, text=True)
        if not done.returncode:
            done = subprocess.run(["gh", "issue", "edit", number, "--add-label", "health:closed"], cwd=root, capture_output=True, text=True)
        print(("FAILED #%s: %s" % (number, done.stderr.strip()[:120])) if done.returncode else "CLOSED #%s" % number)
    return 0
