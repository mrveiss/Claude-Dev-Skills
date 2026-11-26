---
name: memory-library
description: Library-structured Claude Code auto-memory - rooms, shelves (topics), single-author books, chapters, fact files, catalogues and call numbers. Use when a memory topic list has grown too big to read whole and needs shelving (build a shelf from topics/<topic>.md), when looking a memory up (read a shelf card plus one chapter, or a catalogue by topic/author/date/title/kind/issue), when writing a new memory fact (author and created are required, one book per author), or when curating (promoting a session finding to the owner book, archiving a superseded rule, adding a class). Not for deciding what is worth remembering.
---

# Memory library

Invoke as `/claude-dev-skills:memory-library <task> [args]`; the first argument selects the row, otherwise pick it from the situation.
`<mem>` is the memory directory named in the session's system prompt; never hardcode a path.

| Task | When | Reference |
|---|---|---|
| `structure` | Need the model: library, room, shelf, book, chapter, fact; what lives where | `references/structure.md` |
| `lookup` | Answering a question from memory: card first, then ONE chapter; or search by catalogue | `references/lookup.md` |
| `write` | Creating a memory fact; promoting to the owner book; archiving a superseded rule | `references/writing-rules.md` |
| `classify` | Editing `library/classes.json`, reading or building a call number, choosing a code | `references/classification.md` |
| `shelve` | A flat `topics/<topic>.md` is too big: build its shelf and regenerate catalogues | `references/shelving.md` |

Rules that hold without loading a reference:
- Read a shelf card, then one chapter; never a whole topic list (it costs thousands of tokens per question).
- A new fact file carries `author:` and `created:` in `metadata` (a hook blocks it otherwise; file times are reset by copies).
- One book, one author; write only in your own book (a mixed book hides who said what).
- Never hand-edit `library/catalog/**`, cards or generated chapters (they are rebuilt and your edit is lost).
- `build.py` and `catalog.py` never create, change or delete a fact file at the memory root (facts are the record; the library is a view).
