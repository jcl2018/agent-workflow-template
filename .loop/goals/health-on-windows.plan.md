# health-on-windows: plan

1. `skills/workflow-health/scripts/rounds.py` (new): `add` (registry only), `mail_path`, `mail_mode`.
2. `automation.py`: `local register` action and docstring; `workflows.py`: the tick reads the mail file through `register`.
3. `dev/toy/test-health-on-windows.py` (Python, windows: ok) and rows health-register-no-launchd (AUT-1), health-mail-env-named and health-mail-env-windows (AUT-6), each seen red.
4. `docs/wiki/Health.md` output line; DECISIONS.md "Waiting on owner un-review (health-on-windows)" holds the AUT-1, AUT-3, AUT-6 wording.
Risks: the posix mode check must still refuse (toy asserts it on posix); the Mac install path is untouched; scripts stay under 19,000 bytes (workflows.py is already 20,178, only shrunk); package one file bigger.
