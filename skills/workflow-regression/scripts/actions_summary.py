#!/usr/bin/env python3
"""The summary job of the regression workflow: one combined summary after every shard (REG-4, REG-7)."""

SUMMARY_JOB = r"""  summary:
    needs: regression
    if: always()
    runs-on: ubuntu-latest
    timeout-minutes: 10
    permissions:
      contents: read
      issues: write
      pull-requests: read
    steps:
      - uses: actions/checkout@v4
        with:
          persist-credentials: false
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - name: Download every shard's results
        continue-on-error: true
        uses: actions/download-artifact@v4
        with:
          pattern: results-*
          path: ${{ runner.temp }}/shards
      - name: Write one run summary, one table per feature
        continue-on-error: true
        env:
          GH_TOKEN: ${{ github.token }}
          SHARDS: "@SHARDS@"
        run: |
          here=$(mktemp -d)
          cat > "$here/tests.py" <<'TESTS_PY_EOF'
@TESTS@
          TESTS_PY_EOF
          all="$here/results.tsv"; : > "$all"
          reported=0
          for f in "$RUNNER_TEMP"/shards/*/regression-results.tsv; do
            [ -f "$f" ] || continue
            reported=$(( reported + 1 )); cat "$f" >> "$all"
          done
          started=$(sed -n 's/^# started //p' "$all" | sort -n | head -n 1 || true)
          case "$started" in ''|*[!0-9]*) started=$(date +%s) ;; esac  # never an expression
          unrun=$(grep -c '^# unrun ' "$all" || true)
          timeout 120 python3 -I "$here/tests.py" issues --write >/dev/null || true
          took=$(( $(date +%s) - started ))
          {
            GH_TOKEN= python3 -I "$here/tests.py" summary --results "$all" --took "$took" || {
              printf '## Regression\n\nThe grouped summary could not be written; see this step'"'"'s log.\n\n| Test | Result |\n|---|---|\n'
              grep -v '^#' "$all" | awk -F'\t' '{print "| " $1 " | " $2 " |"}'
            }
            printf '\nSHARDS %s of %s reported. UNRUN %s (rows skipped for out of job time).\n' "$reported" "$SHARDS" "$unrun"
          } >> "$GITHUB_STEP_SUMMARY"
"""
