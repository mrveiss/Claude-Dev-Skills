When to use: reading or building a call number, or editing the class schedule.

# Classification

## Class schedule: `<mem>/library/classes.json`

One data file per memory dir; start from `references/classes.example.json` (shelves `CI`, `GIT`, `TEST`). Keys:

| Key | Meaning |
|---|---|
| `rooms` | `{CODE: {dir, title}}`, e.g. `REF` -> `reference` |
| `ledger_cmd` | Optional ledger command (on PATH or a path); `<cmd> sessions` maps names to session ids, env `MEMORY_LIBRARY_LEDGER` overrides. Used only by `authors.py`; omit it and sessions stay unrecorded |
| `shelves` | `{CODE: {name, title, room, source, default_author, authors, chapters, other}}` |
| `shelves.*.source` | Flat topic list to shelve, relative to `<mem>` (`topics/ci-merge.md`) |
| `shelves.*.authors` | `{author: {label, match: {file, line}}}`; regex on fact file name or entry line; first match wins |
| `shelves.*.chapters` | Ordered `{code, key, title, purpose, regex, room?}`; first regex hit wins; `room` moves it (e.g. `ARC`) |
| `shelves.*.other` | Catch-all chapter for entries no regex matches |

- Add a class: add an entry under `shelves` with a short readable uppercase code (`CI`, `GIT`, `TEST`), then run `shelving.md`.
- Codes are part of every call number, so never reuse or rename one once catalogued (old references would dangle).
- A fact's own `author:` frontmatter beats the author `authors.json` records (ledger name for its `originSessionId`), which beats the `authors` match rules.

## Facet order (fixed)

room -> shelf -> author -> chapter -> date

## Call number

`ROOM.SHELF/author/CHAPTER/date`, for example `REF.CI/owner/TRN/2026-11-12`.

- Date source order, with the marker each carries (a date never claims more certainty than its source):

| Marker | Quality | Source |
|---|---|---|
| none, `2026-10-03` | exact | `created:` in the fact, else a date written in the entry |
| `≈` | near-exact | start of the fact's `originSessionId` session |
| `≥` | not-before | newest cited issue/PR `#N`; the line adds `≥2026-09-14 (#19451)` |
| `≥` | range | not-before plus `modified:` as not-after; the line adds `≥2026-09-14 ≤2026-10-01 (#19451)` |
| `≤` | not-after | `modified:` predates the newest cited issue: the citation came in a later edit, so the issue bounds only that edit and the fact is dated no newer than `modified:`; the line adds `≤2026-08-12 (cites #18406 from 2026-10-12: added in a later edit)` |
| `~` | approximate | file time; a day shared by 20 or more file-dated entries is `unknown` |
| `unknown` | none | no usable source |

- Sources 3-4 come from `library/dates.json` (written by `dates.py`, see `shelving.md`); without it the catalogue uses only the first and last rows. `github_repo` in `classes.json` names the repo for `#N` lookups.
- `modified:` is read in the configured zone: an ISO timestamp is converted before taking its day, so an evening UTC edit is not a day early. `dates.py` counts the not-after cases.
- Days are computed in `timezone` from `classes.json` (IANA name), else the machine's local zone.
- by-date groups by the month of the best date; a `≥` entry sits in its not-before month and stays marked; a `≤` entry sits in the month of its `modified:`.
- Sorting call numbers as text gives facet order (that is why the order is fixed).
