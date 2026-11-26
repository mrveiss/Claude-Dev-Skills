When to use: a flat `topics/<topic>.md` is too big to read per question, or catalogues are stale.

# Shelving

Scripts live in `scripts/` (Python standard library only). `<skill>` is this skill's directory; run with `-I`.

1. Ensure `<mem>/library/classes.json` has the shelf (copy `references/classes.example.json` first if absent; edit chapter regexes to the topic).
2. Build the shelf: `python3 -I <skill>/scripts/build.py <mem> <shelf-code-or-name>`.
   - Prints entry counts per author and chapter, and any link whose fact file is missing (fix those at the source).
   - Re-run freely: output is deterministic, stale generated chapters are pruned.
3. Regenerate catalogues: `python3 -I <skill>/scripts/catalog.py <mem>`.
4. Review the `other` chapter (misfiled entries: add a chapter regex or re-shelve) and the by-date `unknown` file (undated bulk-copied entries; add `created:` to fix at the source).
5. Point the topic list's reader at the shelf card (one line in `topics/<topic>.md` or the library README).

- Build and catalog write only under `<mem>/library/` (they refuse any other path), so facts and topic lists stay byte-identical.
- **New fact:** `python3 -I <skill>/scripts/build.py <mem> --fact <file>` rewrites only that fact's chapter, the shelf card and the catalogue groups listing it (byte-identical to a full run); it needs the fact linked from the shelf's source topic list first. It replaces steps 2-3 for one fact.
- **After editing `classes.json`** (chapters, regexes, authors) run the full build (step 2) and catalog (step 3); incremental mode assumes the classes are unchanged.
- Never hand-edit generated output.
- Tests: `python3 -m unittest discover -s <skill>/tests`.
