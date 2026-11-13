# Design: here-refuse (#3468)

Problem: `goal.py new --here` in the repo's main checkout switches it onto a loop branch for hours.
Approaches: (1) refuse everywhere outside loop/worktrees: breaks the ~25 toys that build a goal in a throwaway main checkout. (2) refuse in a main checkout (git dir equals the common dir) of a repo that already has `<common>/loop/worktrees`, i.e. one that runs workers.
Chosen: 2, as `fit.main_here`, called by one line in `cmd_new` (goal.py stays under 20,480 bytes). set, resume and answer are already in references/commands.md; the Delivery Usage section is left alone (drop-usage removes it).
Open questions: none.
