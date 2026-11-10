#!/bin/bash
# Checks that each regression row's # reads: closure covers the skill files its run really reads. Runs each row's
# exact command (identical commands once) from the repo root with a Python audit hook (sitecustomize on PYTHONPATH:
# open, run_file, listdir, scandir, glob) and a python3/python shim first on PATH that logs every launch, then asks
# lanes_cli.py deps for the row's closure. Fails a row on a non-zero exit, on a Python launch the hook never saw
# (LANES-TRACE-NOHOOK: PYTHONPATH reset, or -I/-S), or on a traced skill file outside the closure
# (LANES-TRACE-UNDECLARED, with the # reads: line to add). Reads outside the repo (copied skills) map back to repo
# files by content. Coverage limit: Python reads only; bash reads are covered by the static scan.
# usage: check-reads.sh [--level land|nightly|all] [ROW-ID...]   Writes only to a temp dir it removes.
set -u
here=$(cd "$(dirname "$0")/../.." && pwd)
level=land; [ "${1:-}" = "--level" ] && { level=$2; shift 2; }
tmp=$(mktemp -d); trap 'rm -rf "$tmp"' EXIT
mkdir -p "$tmp/hook" "$tmp/bin"
cat > "$tmp/hook/sitecustomize.py" <<'PY'
import hashlib, os, sys
_log = os.environ.get("LANES_TRACE_LOG")
_root = os.environ.get("LANES_TRACE_ROOT", "") + "/skills/"
_busy = []
if _log:
    _out = open(_log, "a")
    _out.write("MARK %d\n" % os.getpid()); _out.flush()
    def _hook(event, args):
        if event in ("os.listdir", "os.scandir") and \
                sys._getframe(1).f_globals.get("__name__", "").startswith(("importlib", "_frozen_importlib")):
            return  # the import system listing sys.path folders is not the script reading them
        if event in ("open", "cpython.run_file", "os.listdir", "os.scandir", "glob.glob") and args:
            path = args[0]
            if isinstance(path, (str, bytes)) and path:
                path = os.fsdecode(path)
                try:
                    real = os.path.realpath(path)
                    kind = "DIR" if event not in ("open", "cpython.run_file") else "FILE"
                    if kind == "FILE" and not real.startswith(_root) and real.endswith((".py", ".md", ".json")) \
                            and not _busy and os.path.isfile(real):
                        _busy.append(1)  # a copy outside the repo: hash it now, it may be gone by the verdict
                        try:
                            with open(real, "rb") as handle:
                                kind, real = "HASH", hashlib.sha1(handle.read()).hexdigest()
                        finally:
                            _busy.pop()
                    _out.write("%s %s\n" % (kind, real)); _out.flush()
                except (OSError, ValueError):
                    pass
    sys.addaudithook(_hook)
PY
real=$(command -v python3)
for name in python3 python; do
  printf '#!/bin/bash\necho "LAUNCH $$ $*" >> "$LANES_TRACE_LOG"\nexec "%s" "$@"\n' "$real" > "$tmp/bin/$name"
  chmod +x "$tmp/bin/$name"
done
rows=$(python3 - "$here" "$level" "$@" <<'PY'
import sys
here, level, wanted = sys.argv[1], sys.argv[2], set(sys.argv[3:])
seen = {}
for line in open(here + "/.loop/regression.tsv"):
    cells = line.rstrip("\n").split("\t")
    if not line.strip() or line[0] == "#" or len(cells) < 3 or (wanted and cells[0] not in wanted):
        continue
    if not wanted and level != "all" and cells[1] != level:
        continue
    seen.setdefault(cells[2], []).append(cells[0])
for command, ids in seen.items():
    print("\t".join([",".join(ids), command]))
PY
)
fails=0; n=0
while IFS=$'\t' read -r ids command; do
  [ -n "$ids" ] || continue
  n=$((n + 1)); log="$tmp/trace.$n"; : > "$log"
  ( cd "$here" && LANES_TRACE_LOG="$log" LANES_TRACE_ROOT="$(cd "$here" && pwd -P)" PYTHONPATH="$tmp/hook${PYTHONPATH:+:$PYTHONPATH}" PATH="$tmp/bin:$PATH" \
      exec perl -e 'setpgrp(0,0); alarm 600; exec @ARGV' bash -c "$command" ) >"$tmp/out.$n" 2>&1
  rc=$?
  verdict=$(python3 - "$here" "$log" "$command" "$ids" "$rc" <<'PY'
import hashlib, os, re, subprocess, sys
here, log, command, ids, rc = sys.argv[1:]
here = os.path.realpath(here)
launches = marks = 0
reads, dirs = set(), set()
by_hash = {}
for root, _, names in os.walk(os.path.join(here, "skills")):
    for n in names:
        p = os.path.join(root, n)
        if "__pycache__" not in p:
            by_hash.setdefault(hashlib.sha1(open(p, "rb").read()).hexdigest(), os.path.relpath(p, here))
for line in open(log, errors="replace"):
    kind, _, rest = line.rstrip("\n").partition(" ")
    if kind == "LAUNCH":
        launches += 1
    elif kind == "MARK":
        marks += 1
    elif kind in ("FILE", "DIR"):
        if rest.startswith(here + "/skills/"):
            (reads if kind == "FILE" else dirs).add(os.path.relpath(rest, here) + ("/" if kind == "DIR" else ""))
    elif kind == "HASH" and rest in by_hash:
        reads.add(by_hash[rest])
reads = {r for r in reads if "__pycache__" not in r and not r.endswith(".pyc")}
deps = subprocess.run([sys.executable, "-I", os.path.join(here, "skills/workflow-regression/scripts/lanes_cli.py"),
                       "deps", "--root", here, command], capture_output=True, text=True).stdout.splitlines()
always = any(line.startswith("ALWAYS ") for line in deps)
deps = [d for d in deps if not d.startswith("ALWAYS ")]
def covered(p):
    return p in deps or any(d.endswith("/") and p.startswith(d) for d in deps)
out = []
if rc != "0":
    out.append("FAIL %s: the row command exited %s" % (ids, rc))
if launches > marks:
    out.append("LANES-TRACE-NOHOOK %s: %d Python launches, %d hooked (PYTHONPATH reset, or -I/-S?)" % (ids, launches, marks))
if not always:
    for p in sorted(reads | dirs):
        if not covered(p):
            out.append("LANES-TRACE-UNDECLARED %s %s\nfix: # reads: %s" % (ids, p, p))
print("\n".join(out) if out else "PASS %s" % ids)
PY
)
  echo "$verdict"
  case "$verdict" in PASS*) ;; *) fails=$((fails + 1)); tail -5 "$tmp/out.$n" | sed 's/^/  | /' ;; esac
done <<<"$rows"
[ $fails = 0 ] && echo "ALL TRACED: $n commands" || { echo "$fails of $n commands FAILED"; exit 1; }
