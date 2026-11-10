"""health.py's commands other than check: review, judge, preview, file and triage. Each takes the health module (h).

Refusals print REFUSED[code] and exit 2: [file] file with no group, [gh] the issues can't be
listed (nothing is written), [review] a --review FILE that isn't a saved review --json, [why] and [cap] from triage.
"""
import json
import sys


def refuse(code, text):
    print("REFUSED[%s]: %s" % (code, text))
    sys.exit(2)


def cmd_judge(h, args):
    """The check report, then the judge section. The verdict and exit code are the check's, whatever the judge says."""
    root = h.repo_root()
    rows = h.gather(root, None)
    text, _, green, _, _ = h.report(rows)
    print("\n".join(h.with_tests(text, root)))
    print()
    judge = h.sibling_module("judge")
    if not judge:
        print("JUDGE UNAVAILABLE: judge.py is not installed beside health.py")
        return 0 if green else 1
    try:
        answer, why = judge.ask(judge.gather(root, h.HERE, rows), root)
        found = judge.parse(answer)
        if not why and not any(found.values()):
            why = "the answer had no tagged line"
        steps = judge.suggestions(root, rows)[1]
        print("\n".join(judge.render(found, steps)) if not why else "JUDGE UNAVAILABLE: " + why)
    except Exception as error:  # the judge is advice: nothing it does may change the verdict
        print("JUDGE UNAVAILABLE: %s" % str(error)[:120])
    return 0 if green else 1


def cmd_review(h, args):
    """The per-feature repo review. Writes nothing; exit 0 whatever it finds (it is never part of the verdict)."""
    root = h.repo_root()
    review = h.sibling_module("review") or refuse("review", "review.py is not installed beside health.py")
    names = h.sibling_module("feature").features(root)
    if args.feature and args.feature not in names:
        refuse("feature", "unknown feature %s. Features: %s." % (args.feature, ", ".join(sorted(names))))
    found, dropped, why = review.review(root, args.feature)
    if args.json:
        print(json.dumps({"version": 1, "findings": found, "dropped": dropped, "judge": why or "answered"}, indent=2))
    else:
        print("\n".join(review.render(found, dropped, why)))
    return 0


def plan_for(h, root, asked, with_judge, only=None, saved=None):
    """(file module, acts, groups) for the groups asked; exit 2 when file.py or gh can't be used."""
    filing = h.sibling_module("file") or refuse("file", "file.py is not installed beside health.py")
    groups = list(asked or filing.DEFAULT)
    ran = set()
    rows = h.gather(root, [g for g in groups if g in h.ORDER] or None, ran)
    if saved:
        found = h.sibling_module("review").load(saved)
        if found is None:
            refuse("review", "%s is not a saved review --json (version 1). Run: health.py review --json > FILE" % saved)
        rows += h.sibling_module("review").as_rows(found)
        groups.append("review")
    judged, extra = False, []
    if with_judge and "performance" in groups:
        extra, judged = filing.saves(root, h.HERE, rows)
    issues, everything, why = filing.held(root)
    if issues is None:
        refuse("gh", "can't list the issues (%s). Nothing was written." % why)
    return filing, filing.plan(rows, issues, groups, extra, judged, root, ran, everything, only), groups


def cmd_preview(h, args):
    """What file would do. Writes nothing and never runs Mine's private commands unless mine is named."""
    root = h.repo_root()
    asked = h.groups_of(args.group)
    if args.live:
        print("NOTE: run and preview never write, even with --live. To write, run: health.py file --group NAME", file=sys.stderr)
    filing, acts, _ = plan_for(h, root, asked, bool(asked), args.feature, args.review)
    count = filing.preview(acts)
    print("PREVIEW: %d to write, nothing written. To write, run: health.py file --group %s" % (count, args.group or "NAME"))
    return 0


def cmd_file(h, args):
    root = h.repo_root()
    asked = h.groups_of(args.group)
    if not asked and not args.review:
        refuse("file", "file needs --group NAME[,NAME] (one of %s) or --review FILE. Run preview first." % ", ".join(h.NAMES))
    filing, acts, groups = plan_for(h, root, asked or [], True, args.feature, args.review)
    filing.apply(acts, root, groups)
    return 0


def cmd_triage(h, args):
    triage = h.sibling_module("triage") or refuse("triage", "triage.py is not installed beside health.py")
    root = h.repo_root()
    if args.close:
        if not args.kind:
            refuse("kind", "close needs --kind (a group such as docs, or review-gap)")
        return triage.close(root, args.kind, args.why, args.feature, args.older, args.yes, args.max)
    return triage.listing(root, args.feature)


def add(sub, h):
    """Add these commands to health.py's parser."""
    item = sub.add_parser("review", help="the per-feature repo review; writes nothing")
    item.add_argument("--feature")
    item.add_argument("--json", action="store_true")
    item.set_defaults(func=lambda a: cmd_review(h, a))
    for name in ("judge", "suggest"):
        item = sub.add_parser(name, help="the check report, then a judge section of suggestions")
        item.set_defaults(func=lambda a: cmd_judge(h, a))
    for name, func in (("preview", cmd_preview), ("run", cmd_preview), ("file", cmd_file)):
        item = sub.add_parser(name, help="file findings as issues" if name == "file" else "list what file would do")
        item.add_argument("--group", "--family", dest="group", help="NAME[,NAME]: " + ", ".join(h.NAMES))
        item.add_argument("--feature", help="only findings on this feature's milestone")
        item.add_argument("--review", help="a saved health.py review --json to file too")
        item.add_argument("--live", action="store_true", help="(ignored)")
        item.set_defaults(func=lambda a, f=func: f(h, a))
    item = sub.add_parser("triage", help="open findings per feature; --close a batch with the owner's words")
    item.add_argument("--feature")
    item.add_argument("--close", action="store_true")
    item.add_argument("--kind")
    item.add_argument("--why", default="")
    item.add_argument("--older", type=int, default=0)
    item.add_argument("--yes", action="store_true")
    item.add_argument("--max", type=int, default=20)
    item.set_defaults(func=lambda a: cmd_triage(h, a))
