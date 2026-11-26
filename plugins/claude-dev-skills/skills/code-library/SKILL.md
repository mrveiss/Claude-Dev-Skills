---
name: code-library
description: Generated, read-only map of a codebase (rooms = services, shelves = domains, cards, chapters as file:symbol, catalogues by concept, route, env var, Redis key and issue) plus a fork and duplicate report with one entry per class and a proposed canonical home. Use when locating where code lives before grepping, when building or refreshing the map for a commit, or when turning forks and duplicates into one issue and one fix per class. Parses text only; never runs the target repo. Not for memory (use memory-library) and not for enforcing canonical rules in a product.
---

# Code library

Invoke as `/claude-dev-skills:code-library <task> [args]`; the first argument selects the row, otherwise pick it from the situation.
`<map>` is the output directory you pass to the scripts (outside the target repo); `<repo>` is a checkout or an extracted `git archive` of the commit to describe.

| Task | When | Reference |
|---|---|---|
| `structure` | Need the model: room, shelf, card, chapter, catalogue and what each holds | `references/structure.md` |
| `lookup` | Finding where a concept, route, env var, key or issue lives: card or catalogue first, then one chapter | `references/lookup.md` |
| `forks` | Reading the fork/duplicate report, or turning one class into one issue and one fix | `references/forks.md` |
| `classes` | Editing `code-classes.json` (rooms, shelves, schedulers, layers, ignores) | `references/classes.md` |
| `regenerate` | Building or refreshing the map for a commit; running the scripts; the safety guarantees | `references/regeneration.md` |

Rules that hold without loading a reference:
- Read the catalogue line or the domain card, then one chapter; grep only for what the map cannot answer (a call site, a string inside a body).
- The scripts parse file text (`ast`, regex); they never import, run, install or add to `sys.path` anything from the target repo (owner rule: no running code from the codebase).
- Output is written only under `<map>/library/`, never inside the target repo, and every file names the commit it describes; regenerate when the base branch moves, never hand-edit.
- The shared helpers (`write_text`, `call_number`, `prune_generated`, `die`, `slug`) live in `memory-library/scripts/_lib.py`; this skill imports them and holds no copy (the structure model and call-number facets are in `/claude-dev-skills:memory-library structure` and `classify`).
- A subject has one home and a skill one job: see `/claude-dev-skills:coding skill-structure`. Product-side canonical enforcement belongs to the product (AutoBot-AI#22318), not here.
