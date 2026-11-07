# Changelog

## v0.1.1 - 2026-11-07

- Add the regression workflow; record the Codex and CI-like runs
- Say what the Codex and CI-like runs proved

### How to verify

1. Open the repo's Actions tab on GitHub, pick regression, and choose Run workflow on `main`.
   Expect: the run ends green, and every row prints PASS in its log.
