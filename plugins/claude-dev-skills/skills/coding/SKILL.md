---
name: coding
description: Discipline for ANY code change — frontend, backend, infra, migrations, or docs that describe code — and its surrounding workflow: canonical-source rules (never create a helper, wrapper, framework, endpoint, config, schema bootstrap or "v2" of what already exists; which source wins when frontend/backend or plan/doc and code disagree or two implementations of one concept exist), process before coding (explore, plan, debug methodically, verify before claiming done, parallel agents, finishing a branch), clean commits with pre-commit retry, gap audits after a batch fix, and end-of-session memory cleanup. Use whenever writing, modifying, reviewing or planning code; at the start of any non-trivial task, when a bug resists the obvious fix, when about to claim something works, when a plan needs writing, when committing, after a batch fix, and at the end of every session; not for the domain work itself.
---

# Coding

Invoke as `/claude-dev-skills:coding <workflow> [args]`; first argument selects the row; no argument, or an unknown first argument → treat the whole input as args and pick the row from the situation.

| Workflow | When | Reference |
|---|---|---|
| `canonical-coding` | Writing, modifying, reviewing or planning ANY code; tempted to add a helper, wrapper, endpoint, config or "v2"; frontend/backend or plan/doc vs code disagree; two implementations of one concept | `references/canonical-coding.md` |
| `process` | Start of any non-trivial task; exploring a request, planning, debugging a stubborn failure, verifying before "done", dispatching parallel agents, finishing a branch | `references/process.md` |
| `commit` | Committing: pre-flight checks, auto-format, message shape, pre-commit hook retry | `references/commit.md` |
| `gap-audit` | After a batch fix, implementation or remediation: sweep adjacent files for the same defect and file an issue per gap | `references/gap-audit.md` |
| `memory-cleanup` | End of every session: keep MEMORY.md an index and every memory reachable from a topic file | `references/memory-cleanup.md` |

Several rows can apply to one task (typically `canonical-coding` while coding, then `commit`); read each selected reference before acting.
