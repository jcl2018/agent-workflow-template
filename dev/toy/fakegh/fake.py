#!/usr/bin/env python3
"""Milestones and issues for the fake gh. State lives in $FAKE_GH_DIR/milestones.json and issues.json. Dev only."""
import json
import os
import sys

d = os.environ["FAKE_GH_DIR"]
args = sys.argv[1:]


def load(name):
    try:
        return json.load(open(os.path.join(d, name)))
    except (OSError, ValueError):
        return []


def save(name, data):
    json.dump(data, open(os.path.join(d, name), "w"))


def flag(name):
    return args[args.index(name) + 1] if name in args else None


def flags(name):
    return [args[i + 1] for i, a in enumerate(args) if a == name and i + 1 < len(args)]


issues, miles = load("issues.json"), load("milestones.json")
if args[0] == "api":
    if "-f" in args:
        title = next(a[6:] for a in args if a.startswith("title="))
        miles.append({"number": len(miles) + 1, "title": title, "state": "open",
                     "html_url": "https://example.test/milestone/%d" % (len(miles) + 1)})
        save("milestones.json", miles)
        print(json.dumps(miles[-1]))
    else:
        for m in miles:
            mine = [i for i in issues if (i.get("milestone") or {}).get("title") == m["title"]]
            m["open_issues"] = sum(i["state"] == "OPEN" for i in mine)
            m["closed_issues"] = sum(i["state"] == "CLOSED" for i in mine)
        print(json.dumps(miles))
elif args[:2] == ["issue", "list"]:
    if os.environ.get("FAKE_GH_LIST_FAIL"):  # gh cannot read the list: one error line, exit 1
        sys.exit(os.environ["FAKE_GH_LIST_FAIL"])
    pick = [i for i in issues if flag("--milestone") in (None, (i.get("milestone") or {}).get("title"))
            and flag("--state") in (None, "all", i["state"].lower())]
    print(json.dumps(pick[:int(flag("--limit"))] if flag("--limit") else pick))
elif args[:2] == ["issue", "create"]:
    number = len(issues) + 1
    issues.append({"number": number, "title": flag("--title"), "body": flag("--body"), "state": "OPEN",
                   "labels": [{"name": n} for n in flags("--label")],
                   "milestone": {"title": flag("--milestone")} if flag("--milestone") else None,
                   "createdAt": "2026-01-01T00:00:00Z"})
    save("issues.json", issues)
    print("https://example.test/issues/%d" % number)
elif args[:2] in (["issue", "edit"], ["issue", "close"], ["issue", "reopen"], ["issue", "comment"]):
    for i in issues:
        if str(i["number"]) == args[2]:
            if args[1] == "edit":
                if flag("--body") is not None:
                    i["body"] = flag("--body")
                i.setdefault("labels", []).extend({"name": n} for n in flags("--add-label"))
                if flag("--milestone"):
                    i["milestone"] = {"title": flag("--milestone")}
            elif args[1] != "comment":
                i["state"] = "CLOSED" if args[1] == "close" else "OPEN"
    save("issues.json", issues)
elif args[:2] == ["pr", "edit"]:
    open(os.path.join(d, "pr-milestone-" + args[2]), "w").write(flag("--milestone") or "")
