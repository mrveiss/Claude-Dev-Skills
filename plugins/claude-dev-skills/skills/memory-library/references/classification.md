When to use: reading or building a call number, or editing the class schedule.

# Classification

## Class schedule: `<mem>/library/classes.json`

One data file per memory dir; start from `references/classes.example.json` (shelves `CI`, `GIT`, `TEST`). Keys:

| Key | Meaning |
|---|---|
| `rooms` | `{CODE: {dir, title}}`, e.g. `REF` -> `reference` |
| `shelves` | `{CODE: {name, title, room, source, default_author, authors, chapters, other}}` |
| `shelves.*.source` | Flat topic list to shelve, relative to `<mem>` (`topics/ci-merge.md`) |
| `shelves.*.authors` | `{author: {label, match: {file, line}}}`; regex on fact file name or entry line; first match wins |
| `shelves.*.chapters` | Ordered `{code, key, title, purpose, regex, room?}`; first regex hit wins; `room` moves it (e.g. `ARC`) |
| `shelves.*.other` | Catch-all chapter for entries no regex matches |

- Add a class: add an entry under `shelves` with a short readable uppercase code (`CI`, `GIT`, `TEST`), then run `shelving.md`.
- Codes are part of every call number, so never reuse or rename one once catalogued (old references would dangle).
- A fact's own `author:` frontmatter beats the `authors` match rules (the writer knows best).

## Facet order (fixed)

room -> shelf -> author -> chapter -> date

## Call number

`ROOM.SHELF/author/CHAPTER/date`, for example `REF.CI/owner/TRN/2026-11-12`.

- Date source order: `created:` in the fact, then a date written in the entry, then the file time.
- File-time dates are written `~YYYY-MM-DD` (approximate); a day shared by 20 or more file-dated entries is `unknown`.
- Sorting call numbers as text gives facet order (that is why the order is fixed).
