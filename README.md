# AutoBot Skills

Custom [Claude Code](https://claude.com/claude-code) skills for the AutoBot-AI platform — the
working discipline for implementing issues, reviewing and merging PRs, auditing the codebase,
debugging the full stack, and designing UI, distilled into one place.

Copyright © 2026 mrveiss · Apache-2.0.

## Install

Clone into your Claude Code skills directory:

```bash
git clone https://github.com/mrveiss/autobot-skills.git ~/.claude/skills
```

Each skill is a directory with a `SKILL.md`. Claude Code loads them automatically; invoke one
with `/<name>` or let it trigger on the described intent.

## Skills

### Working an issue

- **`implement`** — End-to-end GitHub issue implementation — umbrella gate, worktree, design, code, verify, PR, CI, and the three-gate closure check
- **`drain`** — Pick and solve the backlog issues that need no decision
- **`pr`** — Create a pull request with pre-flight branch checks, targeting Dev_new_gui by default
- **`commit`** — Standardized commit workflow with pre-flight checks, auto-format, and retry logic for pre-commit hooks
- **`pre-merge-validate`** — Validate code before merging — syntax, imports, call-site impact, tests, types, and linting

### Review

- **`review`** — Run a PR review cycle — CI diagnosis, a three-angle finder pass, lint-only auto-fix, and the merge decision
- **`review-fleet`** — Dispatch a 10-angle parallel PR review fleet (finder agents + verifier agents) that posts only confirmed, deduplicated findings to a single PR comment
- **`review-lenses`** — Domain review lenses — architecture, delivery, frontend, documentation, UX, and visual craft

### Auditing a codebase

- **`api-wiring-audit`** — Audit and enforce frontend/backend API contract wiring in AutoBot-AI (or any FastAPI + SPA monorepo)
- **`dead-code-audit`** — Systematic codebase audit for unwired code — identify unregistered routers, uninvoked hooks, orphaned components, and file discovery issues
- **`gap-audit`** — After completing a batch fix or implementation, audit adjacent files for the same issue and file GitHub discovery issues for each gap found
- **`canonical-coding`** — The canonical-source discipline for ALL code changes in this repository
- **`web-audit`** — Full security, SEO, and AI-friendliness audit for any website

### Debugging

- **`debug-autobot`** — Debug any AutoBot failure across the full stack — dispatches parallel investigators per layer (Vue, FastAPI, Redis, ChromaDB, NPU, Browser, AI Stack),

### Design

- **`ui-design`** — Design, build, review, or polish any user interface — visual direction, typography, color, layout, spacing, motion, accessibility, responsive behaviou

### Process & session

- **`process`** — How to approach work before writing code — exploring a request before building, planning a multi-step change, debugging a failure methodically, verify
- **`session-lifecycle`** — Mandatory start-of-session and end-of-session protocol for every Claude Code session in this repository
- **`memory-cleanup`** — End-of-session memory hygiene ritual

### Platform

- **`github-cli`** — Use when performing any GitHub operation — issues, PRs, comments, labels, reviews, merges, file contents, branch management, or repository queries

## Conventions

- **One canonical skill per job.** No `-v2` or `-fix` variants; consolidate rather than fork.
- **A skill is a checklist, not a manual.** Substance beyond a page goes in the skill's own
  `references/` directory and is read on demand.
- Some skills carry local `references/` material adapted from third-party skills for personal
  use; that material is git-ignored and not redistributed here.
