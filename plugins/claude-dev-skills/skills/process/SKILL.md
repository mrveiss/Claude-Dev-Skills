---
name: process
description: How to approach work before writing code — exploring a request before building, planning a multi-step change, debugging a failure methodically, verifying a claim before calling it done, dispatching parallel agents, and finishing a branch. Use at the START of any non-trivial task, when a bug resists the obvious fix, when about to claim something works, or when a plan needs writing. Not for the domain work itself.
---

# Process

The discipline that goes before the code. Self-contained — each section is the actual practice,
not a pointer. When a project's own instructions disagree with anything here, the project wins;
this is technique, not law.

## Brainstorm before building anything new

Before writing a feature, component, or behaviour change, separate *what* from *how*. Say back
the goal in one sentence and name who it is for. Surface the assumptions the request hides — the
unstated input shape, the failure the user actually fears, the case that makes the naive version
wrong. Offer two or three genuinely different approaches with their trade-offs, not one plan
dressed three ways. Only once the intent is pinned do you design. Skipping this is how you build
the wrong thing quickly.

## Write the plan when the change has more than a few steps

A plan is a list of small, individually verifiable steps, each with a way to tell it worked.
Group by responsibility, not by file type — things that change together live together. Name the
risk in each step and what you'll check before moving on. A plan you can't check off step by step
is a wish, not a plan. For work spanning sessions, write it to a file so the next session resumes
from state, not memory.

## Debug by reproducing, never by guessing

When something fails, do not propose a fix from the stack trace alone. First reproduce it
deterministically — the smallest input that triggers it. Then form one hypothesis about the
cause and test *that*, changing one thing at a time. A fix is proven only when it makes the
reproduction pass **and** still rejects the case the code was meant to reject. The most common
error is fixing the predicate you imagined instead of the reproduction in front of you. If three
hypotheses fail, stop and gather more evidence rather than trying a fourth blind change.

## Test-drive the implementation

Before the implementation code, write the test that will fail without it — the one that pins the
behaviour you're about to build. Watch it fail for the right reason (not a typo, not a missing
import). Then write the least code that makes it pass. Assert on behaviour and observable output,
not on source text or internal shape. A test that can't fail proves nothing; a test fed a shape
no producer ever emits proves less than nothing.

## Verify before you claim it's done

"Done", "fixed", and "passing" are claims that need evidence. Run the command and read its output
before you say the words — an empty or absent result is not a pass, it is an unchecked result.
Cite the artifact: the test output, the exit code, the diff, the run link. If you did not run it,
say you did not run it. Never let a green that you assumed stand in for a green that you saw.

## Dispatch parallel agents only for genuinely independent work

Two tasks parallelise cleanly only when neither reads what the other writes and they share no
ordering. When that holds, give each agent an isolated context and a crisp, self-contained brief —
it cannot see your conversation. Prefer a pipeline (each item flows through all stages
independently) over a barrier (wait for every item at each stage) unless a later stage genuinely
needs the whole previous set at once. Collect results, then decide; don't let an agent's raw
output flood back unfiltered.

## Finish the branch before you call the work integrated

Implementation complete is not integrated. Before merging: the tests pass and you saw them pass;
the branch is not behind its base (a green run describes the base it checked out, which may have
moved); nothing new is left unwired — every new module has a caller, or a tracked follow-up says
why not. Then integrate, and only then dispose of the workspace.

## The four that are never optional

1. **Evidence before "done."** Every completion claim cites an artifact.
2. **Reproduce before fixing.** Verify against the failing case *and* the case that must still fail.
3. **Isolate the work.** A worktree or branch per code-touching task; the shared tree stays clean.
4. **Root cause, not workaround.** No TODO-later, no swallowed error. Stuck after three real
   attempts is an escalation with findings, not a fourth guess.

## Traps that recur

- An empty or absent result reads as a clean result — check for the presence of success, not the absence of failure.
- A test that hand-builds its own input passes while production never produces that shape.
- A guard narrower than its own subject reads as coverage while leaving the gap open.
- A green run describes the merge base it checked out; a moved base can invalidate it.
- Run the exploit; do not read the guard and conclude it holds.

## Credits

The practice distilled here was shaped by the [Superpowers](https://github.com/obra/superpowers)
skill suite by Jesse Vincent (obra) and Anthropic's skill-authoring guidance. This text is an
original, self-contained rewrite; for the full upstream treatment of any topic, see that repo.
