---
name: process
description: How to approach work before writing code — exploring a request before building, planning a multi-step change, debugging a failure methodically, verifying a claim before calling it done, dispatching parallel agents, and finishing a branch. Use at the START of any non-trivial task, when a bug resists the obvious fix, when about to claim something works, or when a plan needs writing. Not for the domain work itself.
---

# Process

The approach discipline, in one place. Fourteen process guides live in `references/` — read the
one the task calls for, never the folder.

**CLAUDE.md wins.** Where a reference disagrees with the project or global instructions, the
instructions are canonical. These are technique; the rules are law.

## Route

| Situation | Read |
|---|---|
| A feature, component, or behaviour change is being asked for — before designing it | `references/brainstorming/` |
| A spec exists and a multi-step change needs a written plan | `references/writing-plans/` |
| A written plan needs executing across sessions with checkpoints | `references/executing-plans/` |
| Independent tasks could run at once | `references/dispatching-parallel-agents/` · `references/subagent-driven-development/` |
| A bug, test failure, or unexpected behaviour — **before proposing a fix** | `references/systematic-debugging/` |
| Implementing a feature or bugfix, before writing implementation code | `references/test-driven-development/` |
| About to say "done", "fixed", or "passing" | `references/verification-before-completion/` |
| Asking for, or receiving, code review | `references/requesting-code-review/` · `references/receiving-code-review/` |
| Implementation is complete and needs integrating | `references/finishing-a-development-branch/` |
| An isolated workspace is needed | `references/using-git-worktrees/` |
| Authoring or editing a skill | `references/writing-skills/` |

## The four that are not optional here

Taken from the references above and hardened by this project's own history — these hold even
when the reference is not read:

1. **Evidence before "done".** Every completion claim cites an artifact — issue #, PR link,
   commit SHA, CI status, test output. "Clean" and "all passing" need the run pasted.
2. **Reproduce before fixing.** Verify a fix against the failing reproduction *and* the case that
   must still be caught. Testing the predicate instead of the reproduction proves nothing.
3. **A worktree per code-touching task**, branched off the PR base. The main tree stays read-only.
4. **Root cause, not workaround.** No TODO comments, no swallowed errors, no temp fixes. Stuck
   after three attempts is an escalation with findings, not a fourth attempt.

## Traps this project keeps hitting

- An empty or absent result reads as a clean result — check for presence, not for absence of failure.
- A test that hand-builds its input passes while production never emits that shape.
- A guard narrower than its own subject reads as coverage.
- A green run describes the merge base it checked out, which may have moved.
- Run the exploit; do not read the code and conclude the guard holds.
