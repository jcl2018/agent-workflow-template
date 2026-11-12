# Design: time-ordered estimate selection

The board selects the lowest leave-one-out median error, which lets a goal's prediction use goals completed after it started. The report already calculates a retrospective time-ordered diagnostic, but the board and report can disagree about the model that would have worked in live use.

Approach A: make the existing report diagnostic the selector. This is small but couples board rendering to a CLI report and repeats file loading. Approach B: move the time-ordered fold construction into board_model, score all candidates on the same eligible goals, and leave the existing folds as report diagnostics. This keeps selection and displayed accuracy on one cached score; it costs a little code and changes tests that assumed leave-one-out selection. Choose B.

Done line 1 needs a shared time-ordered score, selection from that score, and a board label that identifies its source. Done line 2 keeps leave-one-out fold and score in board_report. Done line 3 needs an adversarial fixture whose leave-one-out winner differs from the time-ordered winner, registered as a regression row and proved red before implementation.

Open question: the minimum sample threshold currently requires 10 scorable goals. Keep it for this change; eligibility requires a valid start and strictly earlier finish, and every candidate must make a positive prediction for the goal.
