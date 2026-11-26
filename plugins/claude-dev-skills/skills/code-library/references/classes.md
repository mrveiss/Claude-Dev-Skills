When to use: Editing `code-classes.json`: rooms, shelves, schedulers, layers, ignores.

# /claude-dev-skills:code-library classes

Copy `references/code-classes.example.json` next to your map (any path; pass it as `--config`) and edit it. The calling convention for rooms and shelves is memory-library's (`/claude-dev-skills:memory-library classify`); only the keys below are specific to code.

| Key | Meaning |
|---|---|
| `rooms.<CODE>` | `dir` (output directory), `title`, `globs` (repo-relative; `**` spans directories, `*` stays in one) |
| `shelves.<CODE>` | `name` (output directory), `room` (a room code), `globs`; the first matching shelf of the file's room wins |
| `exclude` | globs left out of the map and the report entirely |
| `schedulers.decorators` / `.names` | regexes marking a scheduled job by decorator text or function name |
| `layers.primitive` / `.agent` | globs for the layering that proposes a canonical home; anything else is an orchestrator |
| `fork_ignore_names` | symbol names too common to be forks (`main`, `logger`, ...) |
| `fork_ignore_files` | file names too common to be forks (`utils`, `models`, ...) |
| `fork_skip_paths` | globs never compared (default: `**/alembic/**`, `**/migrations/**`) |

A file in a room but no shelf lands on that room's `other` shelf; a file in no room lands in `unclassified`. With no `--config`, room = first directory and shelf = second (a quick start; call numbers are then truncated).
Keys starting with `_` are comments and are ignored.
