# Design: delivery-usage-here (#3468)

Problem: `goal.py new --here` in the repo's main checkout switches it onto a loop branch for hours; and Delivery's Usage lacks set, resume and answer.
Approaches: (1) refuse whenever the checkout is not under loop/worktrees: breaks the ~25 toys that build a goal in a throwaway main checkout. (2) refuse in a main checkout (git dir equals the common dir) of a repo that already has `<common>/loop/worktrees`, i.e. one that runs workers: protects real repos, leaves fresh toy repos alone.
Chosen: 2, as `fit.main_here`, called by one line in `cmd_new` so goal.py stays under 20,480 bytes. Usage gets three entries and a sentence on `new`.
Open questions: none. The Usage edit needs the owner's re-review (batched by the operation session); nothing is reviewed here.
