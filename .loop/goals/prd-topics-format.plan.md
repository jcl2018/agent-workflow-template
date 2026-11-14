# Plan: prd-topics-format

1. Set `topics` in `.loop/config.json` to the default topics. Done.
2. Re-render Home, README and START.md with criteria.py render, render.py blocks and entry.py write. Done.
3. Add rows home-topic-live and config-holds-topics (each seen red), re-render Tests. Done.
4. Run docs.py check, then qa, ship and pr.

Files: .loop/config.json, docs/wiki/Home.md, docs/wiki/Tests.md, README.md, .loop/START.md, .loop/regression.tsv. No code changes, no requirement wording.
