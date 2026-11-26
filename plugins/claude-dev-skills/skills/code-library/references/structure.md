When to use: Need the map's model: what a room, shelf, card, chapter and catalogue hold, and where each file lands.

# /claude-dev-skills:code-library structure

The map reuses the library shape of `/claude-dev-skills:memory-library structure`; this page lists only what differs for code.

| Library term | Code meaning | File |
|---|---|---|
| room | a top-level service directory, from `code-classes.json` | `library/<room dir>/` |
| shelf | a domain: a group of paths in a room | `library/<room dir>/<shelf dir>/` |
| card | one per domain: entry points, concepts defined, Redis keys and tables, tests importing it, issues cited, chapter list | `CARD.md` |
| chapter | one per source module with symbols: `file:line symbol (kind)`, routes, env vars, keys, importers | `chapters/<path with -- for />.md` |
| catalogue | greppable one-line indexes | `library/catalog/` |
| index | commit, counts, card list | `library/INDEX.md` |

Catalogues (one line per home, `key | detail | file:line | call number`):

| File | Key |
|---|---|
| `catalog/concepts/<first letter>.md` | class, function, module constant, exported TS symbol |
| `catalog/routes.md` | `path METHOD` (router `prefix=` is joined) |
| `catalog/env.md` | env var read by `os.environ`, `os.getenv`, `import.meta.env`, `process.env` |
| `catalog/keys.md` | Redis-key-shaped literals (`word:segment`) and `CREATE TABLE` names |
| `catalog/issues.md` | `#N` cited in a comment, with `file:line` |

Call numbers use memory-library's facet order `room.shelf/author/chapter/date`: the author is always `map` and the date is the commit date.
Entry points detected: FastAPI-style decorators (`@x.get("/p")`), `if __name__ == "__main__"`, and schedulers by decorator or function-name pattern from the config. Tests are files under `tests/`, `test_*.py`, `*_test.py`, `*.test.ts` and `*.spec.ts`; they appear on cards, not in chapters or concept catalogues.
Known limits: only module-level definitions are concepts (methods are used for near-duplicate detection, not listed); `include_router` prefixes are not joined; lowercase module variables are not constants; TS/JS/Vue are read by regex (exports and imports), so they get no body comparison.
