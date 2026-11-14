# health-on-windows: design

Problem: the health round's tick is portable Python, but `local install` refuses off macOS (so no registry is written), the mail file is fixed at `<schedule home>/mail.env`, and the `st_mode & 0o077` check always fails on Windows (it reports 0o66), so a mail.env there is refused as MAIL_ENV_MODE.

Approaches:
1. Make `install` platform-aware (skip the launchd parts on Windows). Touches workflows.py, which is at 20,200 of 20,480 bytes; high risk to the Mac path.
2. Add a small `register.py`: `local register` writes only the registry; `mail_path` honours LOOP_MAIL_ENV; `mail_mode` skips the mode check on Windows. workflows.py only calls the two helpers (its size shrinks). Chosen: the Mac path is unchanged, and the package gains one file.

Done lines: register writes repos.json on a non-Mac platform with no launch agent (toy, three rows); LOOP_MAIL_ENV names the file; Windows mail.env isn't refused while posix still refuses a group-readable file; AUT-1/AUT-3 (and AUT-6) wording drafted in DECISIONS.md, not applied.

Open questions: none for the owner except the wording review.
