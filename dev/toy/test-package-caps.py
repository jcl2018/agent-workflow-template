#!/usr/bin/env python3
# windows: ok
# reads: dev/package.py
"""dev/package.py's caps: a script of 20,480 bytes or more, or a 100th file, makes it fail; the real tree stays inside both."""
import importlib.util
import os
import sys
import tempfile

root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
spec = importlib.util.spec_from_file_location("package", os.path.join(root, "dev", "package.py"))
package = importlib.util.module_from_spec(spec)
spec.loader.exec_module(package)
fails = 0


def check(name, ok):
    global fails
    print(("PASS: " if ok else "FAIL: ") + name)
    fails += 0 if ok else 1


def failures_of(run):
    package.failures.clear()
    run()
    return [str(f) for f in package.failures]


def script(folder, size):
    os.makedirs(os.path.join(folder, "skills", "workflow-x", "scripts"), exist_ok=True)
    text = "#!/usr/bin/env python3\nimport sys\nsys.exit(0)\n"
    path = os.path.join(folder, "skills", "workflow-x", "scripts", "big.py")
    with open(path, "w", newline="\n") as handle:
        handle.write(text + "#" * (size - len(text) - 1) + "\n")
    return "skills/workflow-x/scripts/big.py"


with tempfile.TemporaryDirectory() as tmp:
    ok = failures_of(lambda: package.check_scripts(tmp, [script(tmp, package.MAX_SCRIPT - 1)]))
    check("a script of 20,479 bytes passes", not ok)
    big = failures_of(lambda: package.check_scripts(tmp, [script(tmp, package.MAX_SCRIPT)]))
    check("a script of 20,480 bytes fails", any("20 KB" in f for f in big))

with tempfile.TemporaryDirectory() as tmp:
    names = []
    for n in range(package.MAX_FILES + 1):
        name = "f%03d.md" % n
        with open(os.path.join(tmp, name), "w") as handle:
            handle.write("x\n")
        names.append(name)
    check("99 files pass the size rule", not [f for f in failures_of(lambda: package.check_files(tmp, names[:package.MAX_FILES])) if "files" in f])
    check("a 100th file fails it", any("100" in f for f in failures_of(lambda: package.check_files(tmp, names))))

shipped = package.walk(root)
check("the real tree ships at most 99 files (%d)" % len(shipped), len(shipped) <= package.MAX_FILES)
long = [r for r in shipped if r.endswith(".py") and len(package.read(root, r)) >= package.MAX_SCRIPT]
check("every real script is under 20,480 bytes" + (": " + ", ".join(long) if long else ""), not long)
sys.exit(1 if fails else 0)
