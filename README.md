# Claude Dev Skills

A portable [Claude Code](https://claude.com/claude-code) plugin — the development discipline for
implementing issues, reviewing and merging PRs, auditing a codebase, debugging the full stack,
and designing UI, packaged as one installable set. Kept separate from any project so the setup
moves to a new machine with a single install.

Copyright © 2026 mrveiss · Apache-2.0.

## Install

This repo is a Claude Code plugin marketplace. In Claude Code:

```
/plugin marketplace add mrveiss/Claude-Dev-Skills
/plugin install claude-dev-skills@claude-dev-skills
```

The first command registers the marketplace; the second installs the skill set. On a new machine,
those two lines restore the whole setup.

## Skills

### Process & discipline

- **`process`** — How to approach work before writing code — exploring a request before building, planning a multi-step change, debugging a failure methodical
- **`commit`** — Standardized commit workflow with pre-flight checks, auto-format, and retry logic for pre-commit hooks
- **`canonical-coding`** — The canonical-source discipline for ALL code changes in this repository

### Review & audit

- **`review-lenses`** — Domain review lenses — architecture, delivery, frontend, documentation, UX, and visual craft
- **`gap-audit`** — After completing a batch fix or implementation, audit adjacent files for the same issue and file GitHub discovery issues for each gap found
- **`web-audit`** — Full security, SEO, and AI-friendliness audit for any website

### Design

- **`ui-design`** — Design, build, review, or polish any user interface — visual direction, typography, color, layout, spacing, motion, accessibility, responsiv

### Memory

- **`memory-cleanup`** — End-of-session memory hygiene ritual

## Layout

```
.claude-plugin/marketplace.json          the marketplace manifest
plugins/claude-dev-skills/
  .claude-plugin/plugin.json             the plugin manifest
  skills/<name>/SKILL.md                 one skill each
```

## Acknowledgments

Two skills here consolidate and adapt the work of other skill authors. The `SKILL.md` router
files are original to this repo, but they stand on ideas — and, on the dev machine, local
`references/` material — from the skills below. That reference material is **not redistributed
here** (it stays git-ignored); credit and thanks go to its authors:

- **`process`** consolidates the [Superpowers](https://github.com/obra/superpowers) skill suite
  by **Jesse Vincent** (`obra`) — brainstorming, TDD, systematic debugging, verification,
  planning, worktrees, and the subagent workflows. Its skill-authoring guidance also points to
  **Anthropic's** official best practices.
- **`ui-design`** consolidates five design skills: the polish-and-motion guidance encodes
  **Emil Kowalski's** philosophy on UI detail and animation; `frontend-design` is **Anthropic's**
  (from `claude-plugins-official`); and the systems/stacks, anti-slop, and audit lenses come from
  the **ui-ux-pro-max**, **taste-skill**, and **impeccable** skills respectively.

Where an author's name was not recorded in the source, the skill is credited by its name. If you
authored one of these and want different or removed attribution, open an issue.

## Conventions

- **One canonical skill per job.** No `-v2` or `-fix` variants; consolidate rather than fork.
- **A skill is a checklist, not a manual.** Substance beyond a page lives in the skill's own
  `references/` directory and is read on demand.
- Two skills (`ui-design`, `process`) can carry extra `references/` material adapted from
  third-party skills for local enrichment. That material is git-ignored and not distributed; the
  router `SKILL.md` stays useful without it.
