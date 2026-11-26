When to use: Finding where a concept, route, env var, key or issue lives in a mapped codebase.

# /claude-dev-skills:code-library lookup

1. Know the name? Grep the one catalogue file (`catalog/concepts/<first letter>.md`, `routes.md`, `env.md`, `keys.md`, `issues.md`) for `^name |`. The line gives `file:line` and the call number.
2. Several homes on the catalogue means a fork or duplicate: open `forks/REPORT.md` for that concept (`/claude-dev-skills:code-library forks`) before choosing one.
3. Know only the area? Open `library/INDEX.md`, then the domain's `CARD.md` (entry points, concepts, tests, issues).
4. Read ONE chapter (`chapters/<module>.md`) for symbols, routes and importers of that module; then open the source at the `file:line`.
5. Check the `commit:` line first: a map older than the base branch can name a moved line; regenerate (`/claude-dev-skills:code-library regenerate`) instead of trusting it.
6. Fall back to grep for what the map does not index: call sites, strings inside bodies, lowercase module variables, TS bodies.
