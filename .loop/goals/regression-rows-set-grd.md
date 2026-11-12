# Add regression rows for SET-6, SET-7 and SET-9 (#338 #339 #341) and GRD-1 to GRD-10 (#815 to #824), each seen red once, and the missing del8-session-tokens and GRD-3 hook-bypass rows

- Slug: regression-rows-set-grd
- Touches: not declared

## Done lines

Frozen. A wrong done line needs a new goal.

1. every SET-6/7/9 and GRD-1..10 requirement has a regression row seen red, and issues #338 #339 #341 #815 to #824 are closed

## Verify by hand

<!-- Numbered steps for a person, each with an Expect: line. A release needs this. -->
1. Run `python3 skills/workflow-regression/scripts/regression.py sync`.
   Expect: no GAP line names SET-6, SET-7, SET-9 or GRD-1 to GRD-10 as lacking a row, and no UNPROVEN line names a grd row.
2. Run `grep -c '^grd' .loop/regression.tsv`.
   Expect: 17 or more rows.

