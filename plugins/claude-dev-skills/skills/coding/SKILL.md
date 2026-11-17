---
name: coding
description: Discipline for any code change and its surrounding workflow — canonical-source rules (never create a helper, wrapper, "v2", endpoint or config that already exists; which source wins when frontend/backend or doc/code disagree), process before coding (explore, plan, debug methodically, verify before claiming done, parallel agents, finishing a branch), clean commits with pre-commit retry, gap audits after a batch fix, and end-of-session memory cleanup. Use whenever writing, modifying, reviewing or planning code, at the start of any non-trivial task, when committing, after a batch fix, or at the end of a session.
---

# Coding

Invoke as `/claude-dev-skills:coding <workflow> [args]`; first argument selects the row; no argument → pick the row from the situation.

| Workflow | When | Reference |
|---|---|---|
| `canonical-coding` | Writing, modifying, reviewing or planning ANY code; tempted to add a helper, wrapper, endpoint, config or "v2"; frontend/backend or plan/doc vs code disagree; two implementations of one concept | `references/canonical-coding.md` |
| `process` | Start of any non-trivial task; exploring a request, planning, debugging a stubborn failure, verifying before "done", dispatching parallel agents, finishing a branch | `references/process.md` |
| `commit` | Committing: pre-flight checks, auto-format, message shape, pre-commit hook retry | `references/commit.md` |
| `gap-audit` | After a batch fix, implementation or remediation: sweep adjacent files for the same defect and file an issue per gap | `references/gap-audit.md` |
| `memory-cleanup` | End of every session: keep MEMORY.md an index and every memory reachable from a topic file | `references/memory-cleanup.md` |

Several rows can apply to one task (typically `canonical-coding` while coding, then `commit`); read each selected reference before acting.
