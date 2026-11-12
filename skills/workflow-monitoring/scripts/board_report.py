#!/usr/bin/env python3
"""Why the live board uses the estimate model it does: the time-ordered backtest of every candidate in board_model.py over
a repo's finished goals, with diagnostics. It only reads files and runs git rev-parse; it writes nothing.

usage: board_report.py [--root DIR] [--json]

One row per candidate: its selection score (the median over finished goals of |ln(estimate / actual)| for the whole goal,
in log units and as xN.NN, how many times off it typically was either way), the goals scored, then diagnostics only:
the leave-one-out score, the share of goals inside the
queued range, the 90th-percentile error, the share underestimated and the per-step score. The last lines say which one
the board uses and why, and the gap between the two lowest scores. --json prints the same as one JSON object.
Refusals (exit 1): NO_REPO (DIR is not inside a git repo), RUNS_UNREADABLE (the runs folder cannot be read). A run file
that cannot be parsed is skipped with a BAD_RUN line on stderr.
"""
EXAMPLE = "example: python3 skills/workflow-monitoring/scripts/board_report.py --root ."
import argparse
import datetime
import json
import math
import os
import statistics
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import board_model as bm  # noqa: E402
from board_log import STEPS, git  # noqa: E402


def load(root):
    """(runs, folder, skipped, files): every run record under <git common dir>/loop/runs with a slug and not retired."""
    folder = os.path.join(os.path.abspath(os.path.join(root, git("rev-parse", "--git-common-dir", cwd=root))), "loop", "runs")
    if not os.path.isdir(folder):
        return [], folder, 0, 0
    try:
        names = sorted(n for n in os.listdir(folder) if n.endswith(".json"))
    except OSError as error:
        sys.exit("REFUSED: cannot read %s: %s (RUNS_UNREADABLE). Check the folder's permissions; nothing was changed." % (folder, error))
    runs, skipped = [], 0
    for name in names:
        path = os.path.join(folder, name)
        try:
            with open(path) as handle:
                run = json.load(handle)
        except (OSError, ValueError) as error:
            skipped += 1
            print("board_report: skipped %s: %s (BAD_RUN)" % (path, error), file=sys.stderr)
            continue
        if isinstance(run, dict) and run.get("slug") and run.get("status") != "retired":
            runs.append(run)
    return runs, folder, skipped, len(names)


def share(flags):
    return {"share": round(sum(flags) / len(flags), 3) if flags else None, "of": len(flags)}


def step_score(rows, name):
    errors = [abs(math.log(r["per"][name][s][0] / r["seconds"][s])) for r in rows for s in STEPS
              if r["seconds"].get(s) and r["per"][name].get(s) and r["per"][name][s][0]]
    return round(statistics.median(errors), 3) if errors else None


def report(root):
    runs, folder, skipped, files = load(root)
    at = datetime.datetime.now(datetime.timezone.utc)
    bm.MODEL.clear()
    began = time.time()
    _, n = bm.backtest(runs, at, root)
    elapsed = time.time() - began
    name = bm.chosen(runs, at, root)
    rows = bm.MODEL.get("folds") or []
    loo_rows = bm.folds(bm.MODEL["hist"], bm.CANDIDATES, bm.MODEL)
    out = {"candidates": [], "chosen": name, "reason": bm.MODEL["chosen"][1], "n": n, "elapsed_s": round(elapsed, 3),
           "skipped": {"files": skipped, "of": files}, "runs": folder}
    for c in bm.CANDIDATES:
        errs = sorted(abs(math.log(r["left"][c] / r["actual"])) for r in rows)
        low = [sum(b[1] for b in r["per"][c].values() if b) for r in rows]
        high = [sum(b[2] for b in r["per"][c].values() if b) for r in rows]
        loo = round(bm.score(loo_rows, c), 3) if loo_rows else None
        ordered = round(bm.score(rows, c), 3) if rows else None
        out["candidates"].append({
            "id": c, "label": bm.LABELS[c], "score": ordered, "x": round(math.exp(ordered), 2) if ordered is not None else None, "n": len(rows),
            "time_ordered": {"score": ordered, "n": len(rows), "of": len(bm.MODEL["done"])},
            "leave_one_out": {"score": loo, "n": len(loo_rows)},
            "in_range": share([lo <= r["actual"] <= hi for r, lo, hi in zip(rows, low, high)]),
            "p90": round(statistics.quantiles(errs, n=10, method="inclusive")[-1] if len(errs) > 1 else errs[0], 3) if errs else None,
            "under": share([r["left"][c] < r["actual"] for r in rows]), "step_score": step_score(rows, c)})
    ranked = sorted(x["score"] for x in out["candidates"] if x["score"] is not None)
    out["gap"] = round(ranked[1] - ranked[0], 3) if len(ranked) > 1 else None
    return out


def text(out):
    if not out["n"]:
        return ["board_report: 0 of %d scorable goals under %s; the board uses the size rule until %d finished goals have "
                "logged time." % (bm.MIN_BACKTEST, out["runs"], bm.MIN_BACKTEST)]
    dash = lambda v, f="%.3f": "-" if v is None else f % v
    row = "%-22s %9s %7s %4s | %-22s %-11s %6s %-11s %s"
    lines = ["board_report: %d scorable goals under %s, backtest %.2fs" % (out["n"], out["runs"], out["elapsed_s"]),
             row % ("candidate", "time score", "x", "n", "diagnostics: loo", "in range", "p90", "under", "per-step")]
    for c in out["candidates"]:
        t, r, u = c["leave_one_out"], c["in_range"], c["under"]
        lines.append(row % ("%s (%s)" % (c["id"], c["label"]), dash(c["score"]), dash(c["x"], "x%.2f"), c["n"],
                            "%s (%d goals)" % (dash(t.get("score")), t.get("n", 0)),
                            "%s of %d" % (dash(r["share"], "%.2f"), r["of"]), dash(c["p90"]),
                            "%s of %d" % (dash(u["share"], "%.2f"), u["of"]), dash(c["step_score"])))
    lines.append("time-ordered selection (retrospective, current sizes): each goal predicted only from goals finished before it started")
    lines.append("chosen: %s, %s" % (out["chosen"], out["reason"]))
    if out["gap"] is not None:
        lines.append("gap between the two lowest scores: %.3f" % out["gap"])
    return lines


def main():
    parser = argparse.ArgumentParser(description=__doc__, epilog=EXAMPLE, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--root", help="a folder inside the repo (default: the current repo)")
    parser.add_argument("--json", action="store_true", help="print one JSON object and nothing else")
    args = parser.parse_args()
    where = args.root or "."
    root = git("rev-parse", "--show-toplevel", cwd=where) if os.path.isdir(where) else ""
    if not root:
        sys.exit("REFUSED: %s is not inside a git repo (NO_REPO). Pass --root with a repo path, or run from inside one." % where)
    out = report(root)
    if out["skipped"]["files"]:
        print("board_report: skipped %d of %d run files" % (out["skipped"]["files"], out["skipped"]["of"]), file=sys.stderr)
    print(json.dumps(out, indent=1) if args.json else "\n".join(text(out)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
