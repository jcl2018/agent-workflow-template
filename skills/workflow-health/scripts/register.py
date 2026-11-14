"""The schedule on a machine that has no launch agent (a Windows PC): register a repo for the tick, and find the mail file.

local register   what install does for the registry, with no launchd and no platform check; the owner's scheduler runs
                 `automation.py local tick --scheduled`.
mail_path        LOOP_MAIL_ENV names the mail file, else <schedule home>/mail.env.
mail_mode        "" when the file may be read; MAIL_ENV_MODE for a file others can read. Windows has no mode bits, so it never refuses there.
"""
import os
import sys


def mail_path(home):
    return os.environ.get("LOOP_MAIL_ENV") or os.path.join(home, "mail.env")


def mail_mode(path):
    return "MAIL_ENV_MODE" if os.name != "nt" and os.stat(path).st_mode & 0o077 else ""


def add(w, root, cfg):
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
