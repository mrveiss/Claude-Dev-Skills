When to use: creating or changing a memory fact, promoting a finding, or retiring a rule.

# Writing rules

- **One book per author** (so every rule traces to one voice): `owner` for rules the owner states, else your session name.
- **`author:` and `created: YYYY-MM-DD` under `metadata`** on every new fact (file times are unreliable; the hook blocks a new file without them):
  ```
  ---
  name: ...
  description: ...
  metadata:
    type: feedback
    author: owner
    created: 2026-11-12
  ---
  ```
- **Write only in your own book** (editing another author's entry rewrites their record); a disagreement is a new entry in your book.
- **Promotion into the owner book needs the owner's approval** (the owner book outranks all others); mark the session entry as moved, never silently copy.
- **Superseded rules go to the archive room** (the live chapter keeps only the current rule); the archived entry names its replacement.
- Facts are never deleted by build or catalog; deleting or rewriting stored memory stays a human-approved act.
- Index it: add the one-line pointer to the matching `topics/*.md` (see `coding` -> `memory-cleanup`), then run the incremental build for the new fact (`--fact`; when to use it and when a full build is needed: `shelving.md`).
- Exempt from the hook: `MEMORY.md`, `topics/**`, `library/**`, and edits to files that already exist.
