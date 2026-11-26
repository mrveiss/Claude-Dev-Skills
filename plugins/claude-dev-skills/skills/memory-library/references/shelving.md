When to use: a flat `topics/<topic>.md` is too big to read per question, or catalogues are stale.

# Shelving

Scripts live in `scripts/` (Python standard library only). `<skill>` is this skill's directory; run with `-I`.

1. Ensure `<mem>/library/classes.json` has the shelf (copy `references/classes.example.json` first if absent; edit chapter regexes to the topic).
2. Attribute authors: `python3 -I <skill>/scripts/authors.py <mem>` (writes `library/authors.json`: fact -> `{author, source}`). Source order: `author:` frontmatter, then the ledger name recorded for the fact's `originSessionId` (`ledger_cmd`, see `classification.md`), else `unrecorded`; an author is never guessed. Without a ledger it says so and leaves those facts unrecorded. `build.py` places books by it, so it runs first and needs no build output.
3. Build the shelf: `python3 -I <skill>/scripts/build.py <mem> <shelf-code-or-name>`.
   - Prints entry counts per author and chapter, and any link whose fact file is missing (fix those at the source).
   - Entries linking to a URL (`https://...`) are external: shelved and catalogued like any line, never fact files, never reported missing; dated only from text in the line, else `unknown`.
   - Re-run freely: output is deterministic, stale generated chapters are pruned.
4. Date the facts: `python3 -I <skill>/scripts/dates.py <mem>` (writes `library/dates.json`, caches issue/PR dates in `library/ref-dates.json`). It needs `github_repo` in `classes.json` and `gh` for the `#N` source, fetched in GraphQL batches of 50; without them it skips that source and says so. A number the response lacks is a failure: not cached, retried next run.
5. Regenerate catalogues: `python3 -I <skill>/scripts/catalog.py <mem>` (the by-author catalogue counts resolved vs unrecorded authors).
6. Review the `other` chapter (misfiled entries: add a chapter regex or re-shelve) and the by-date `unknown` file (undated bulk-copied entries; add `created:` to fix at the source).
7. Point the topic list's reader at the shelf card (one line in `topics/<topic>.md` or the library README).

- Build, authors, dates and catalog write only under `<mem>/library/` (they refuse any other path), so facts and topic lists stay byte-identical.
- **Run the full build (steps 2-5: authors → build → dates → catalog) after a new fact and after editing `classes.json`.** Unchanged generated files are not rewritten, so a new fact changes only its chapter, the shelf card and the catalogue files listing it, and every other file keeps its content and mtime.
- Never hand-edit generated output.
- Tests: `python3 -m unittest discover -s <skill>/tests`.
