# hooks-once design

Problem: #2880 saw setup.py --reply-hook then --govern-hook leave two identical govern hooks. Main already collapses repeats on POSIX (agents.reply_hook matches its own entries by "/<name>'" and rewrites to one), but on Windows the command holds a backslash path, so no existing entry matched and every install appended another.

Approaches: (A) match its own entry after normalizing backslashes to slashes (one line); (B) store a marker key in each entry (changes the settings format).

Chosen: A. agents.py stays under the cap (20,367 bytes). A Python toy (dev/toy/test-hooks-once.py) runs setup.py four times plus a duplicate-fixture case in a throwaway repo; row set13-hooks-once.

Open questions: none.
