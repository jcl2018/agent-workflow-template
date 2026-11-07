# Make every workflow script exit with a clear error instead of waiting, when it would need input and no terminal is attached

- Slug: no-tty-refuse
- Touches: skills

## Done lines

Frozen. A wrong done line needs a new goal.

1. Running any workflow script with standard input closed, such as < /dev/null, never waits for input; it exits with an error naming what it needed
2. Scripts that need no input behave exactly as before
3. The Health or Delivery wiki page says that scripts refuse rather than wait when no terminal is attached

## Verify by hand

<!-- One or more numbered steps a person can follow, each with an Expect: line. Every release needs this. -->
