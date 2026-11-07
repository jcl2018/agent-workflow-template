<!-- workflow-docs -->
# Regression

Skill: `workflow-regression`. Keeps tests visible and enforced. Rows live in `.loop/regression.tsv`. Script:
`regression.py`.

## Commands

```text
seed
add <id> --level <level> --command "<command>" [--goal <slug>:<n>]
sync [--write]
red <id> --break "<command>"
run [land|nightly|<id>] [--timeout S] [--live]
workflow
```

| Level | Runs in |
|---|---|
| `land` | `run land` and `run nightly` |
| `nightly` | `run nightly` |
| `draft` | Nothing, until given a real command |
| `covered` | Nothing; proved elsewhere |

- `seed` adds a `land` row for each check in the config.
- `sync` lists done lines with no row (`GAP`), `DRAFT` rows and `UNPROVEN` rows; `--write` adds drafts.
- `red` copies `HEAD` to a temporary worktree, applies the break and records the date if the test fails. `STILL GREEN`
  means the test proves nothing.
- `run` prints `PASS`, `FAIL`, `KNOWN`, `FIXED` or `UNPROVEN` (blocks). Known failures sit in
  `.loop/regression-known.tsv`. It keeps one issue per failing row; without a token it only prints `WOULD` lines.
- `workflow` writes `.github/workflows/regression.yml` (nightly, on `v*` tags, by hand).

## Example

```bash
python3 scripts/regression.py red check-1 --break "sed -i.bak 's/return a + b/return a - b/' calc.py"
python3 scripts/regression.py run land
```
