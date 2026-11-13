"""check --own: a stale page the goal's own diff doesn't touch is a FINDING, not a failure.

A goal's pr lane merges main and runs docs check on the merged head. One page already stale on main would fail every goal.
So with --own, a STALE line for a mapped page whose paths the goal's diff (merge-base with main..HEAD) never touches is moved
to the notes as FINDING, said and not failed. Plain check (health, the scheduled run, main itself) is unchanged, so main's
staleness stays visible there. Pages not in the map (generated pages, entry files) still fail: they follow from the goal's
own commits."""
import subprocess


def git(root, *args):
    out = subprocess.run(["git"] + list(args), cwd=root, capture_output=True, text=True)
    return out.stdout.strip() if out.returncode == 0 else None


def base_ref(root, name):
    for ref in ("origin/" + name, name):
        if git(root, "rev-parse", "--verify", "-q", ref + "^{commit}"):
            return ref
    return None


def touched(root, ref, paths):
    """True when the goal's diff (merge-base of ref and HEAD, to HEAD) touches any of the page's mapped paths."""
    out = git(root, "diff", "--name-only", ref + "...HEAD", "--", *paths)
    return out is None or bool(out)  # no diff answer: judge the page as the goal's own


def split(root, found, notes, rows, name="main"):
    """(found, notes) with each STALE line of an untouched mapped page moved to notes as FINDING."""
    ref = base_ref(root, name)
    if not ref:
        return found, notes
    keep, moved = [], []
    for item in found:
        if item[0] == "STALE" and item[1] in rows and not touched(root, ref, rows[item[1]]):
            moved.append(("FINDING", "STALE " + item[1], item[2] + " (not touched by this goal; main's own, left for health)"))
        else:
            keep.append(item)
    return keep, notes + moved
