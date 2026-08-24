# Claude Dev Skills

A portable [Claude Code](https://claude.com/claude-code) plugin — a set of eight general-purpose
development skills that encode *how to work*: exploring a request before building, planning and
debugging methodically, reviewing and auditing, designing UI, committing cleanly, and keeping
memory tidy. Packaged as one marketplace plugin so the whole working discipline moves to a new
machine in two commands.

> **Origin.** These skills emerged while developing
> [AutoBot-AI](https://github.com/mrveiss/AutoBot-AI) — a distributed autonomous-agent platform.
> They are the general, project-agnostic half of that discipline, extracted so the practice
> travels beyond the project that produced it. The AutoBot-specific skills (issue implementation,
> PR mechanics, stack debugging) live in
> [AutoBot-AI-Claude-dev-skills](https://github.com/mrveiss/AutoBot-AI-Claude-dev-skills).

Copyright © 2026 mrveiss · Apache-2.0.

---

## Install

This repository is a Claude Code **plugin marketplace**. Install from inside Claude Code:

```
/plugin marketplace add mrveiss/Claude-Dev-Skills
/plugin install claude-dev-skills@claude-dev-skills
```

or from a terminal with the Claude Code CLI:

```bash
claude plugin marketplace add mrveiss/Claude-Dev-Skills
claude plugin install claude-dev-skills@claude-dev-skills
```

**What each step does.** `marketplace add` clones this repo into Claude Code's marketplace cache
and validates `.claude-plugin/marketplace.json`. `install` copies the plugin into the plugin
cache and enables it for your user scope. Both are recorded in your `~/.claude/settings.json`
(`extraKnownMarketplaces` and `enabledPlugins`), so the state is declarative and reproducible.

**Verify the install:**

```bash
claude plugin list          # claude-dev-skills should show ✔ enabled
```

**On a new machine**, the same two commands restore the entire set — nothing else to copy.

> Skills are read fresh on each invocation, so an update to the installed plugin takes effect
> without restarting a conversation. New skills added to the plugin appear after the next
> `claude plugin marketplace update`.

---

## Using the skills

Skills load automatically and trigger two ways:

1. **By intent.** Each skill's `description` tells Claude when it applies. Ask for the underlying
   task in plain language — "help me plan this migration", "review this design", "audit the repo
   for the same bug" — and the matching skill activates. You do not name it.
2. **Explicitly.** Invoke one directly with a slash command: `/process`, `/ui-design`,
   `/web-audit`, and so on.

Each skill is self-contained: everything it needs is in its `SKILL.md`. There are no external
files to fetch and nothing to configure before first use.

---

## The eight skills

### Process & discipline

- **`process`** — The approach discipline that goes *before* the code: brainstorming intent
  before building, writing a checkable plan, debugging by reproduction instead of guessing,
  test-driving the implementation, verifying a claim before calling it done, dispatching parallel
  agents only for truly independent work, and finishing a branch cleanly. Use at the start of any
  non-trivial task.
- **`commit`** — A standardized commit workflow: pre-flight branch and staging checks,
  auto-format, conventional-commit message shape, and retry logic when a pre-commit hook rewrites
  files.
- **`canonical-coding`** — The canonical-source discipline: before adding a helper, wrapper, or
  "v2" of anything, find the existing one and consolidate. Defines which source wins when a
  frontend and backend, or a doc and the code, disagree.

### Review & audit

- **`review-lenses`** — Six domain lenses for judging whether work is *good*, not merely whether
  it runs — architecture, delivery, frontend, documentation, UX, and visual craft. Use for any
  "is this good?" review.
- **`gap-audit`** — After a batch fix, sweep the adjacent files for the same defect and file a
  discovery issue per gap found, so a fix in one place doesn't leave siblings broken.
- **`web-audit`** — A full multi-pass security, SEO, and AI-friendliness audit of any website —
  HTTP headers, TLS, CORS, DNS/subdomain recon, exposed panels, per-page SEO and performance —
  emitting a self-contained HTML report.

### Design

- **`ui-design`** — One skill for every interface job: choosing an aesthetic direction that
  doesn't look templated, auditing an existing UI, redesigning without going generic, component
  polish and motion, and building a token-based design system. Self-contained, framework-agnostic.

### Memory

- **`memory-cleanup`** — An end-of-session hygiene ritual for a file-based memory system: keep the
  index an index, ensure every entry is reachable from a topic file, and prune what has gone
  stale or duplicated.

---

## Updating

```bash
claude plugin marketplace update claude-dev-skills   # pull the latest from this repo
```

Updates to an already-installed skill flow through on the next read. A newly *added* skill
becomes available after the marketplace update above.

## Uninstalling

```bash
claude plugin uninstall claude-dev-skills@claude-dev-skills
claude plugin marketplace remove claude-dev-skills     # optional: forget the marketplace too
```

---

## Contributing

1. **One skill = one responsibility.** If a `SKILL.md` grows past ~700 lines, split it.
2. **Every published skill must be self-contained.** A skill's `SKILL.md` may not depend on files
   that aren't committed — an installer only receives what ships. Two skills (`process`,
   `ui-design`) keep optional local `references/` enrichment on the dev machine; that material is
   git-ignored and **not** required for the skill to work.
3. **Edit → PR → review.** Workflow-rule changes get the same review as code. State in the PR what
   behaviour changed and why.
4. **Write the `description` for triggering.** It is how Claude decides when the skill applies —
   name the situations, not the mechanics.

## Layout

```
.claude-plugin/marketplace.json          the marketplace manifest
plugins/claude-dev-skills/
  .claude-plugin/plugin.json             the plugin manifest
  skills/<name>/SKILL.md                 one self-contained skill each
```

---

## Acknowledgments

Two skills distill the work of other skill authors into original, self-contained rewrites. Their
`SKILL.md` text is written fresh for this repo — it does not redistribute the source material —
but the practice it captures is owed to:

- **`process`** — the [Superpowers](https://github.com/obra/superpowers) skill suite by
  **Jesse Vincent** (`obra`): brainstorming, TDD, systematic debugging, verification, planning,
  worktrees, and the subagent workflows, plus **Anthropic's** skill-authoring guidance. For the
  full upstream treatment of any topic, see that repo.
- **`ui-design`** — five design skills: **Emil Kowalski's** philosophy on UI polish and motion,
  **Anthropic's** `frontend-design`, and the **ui-ux-pro-max**, **taste-skill**, and
  **impeccable** skills for systems, anti-slop redesign, and audit lenses.

Where an author's name was not recorded in the source, the skill is credited by its name. If you
authored one of these and want different or removed attribution, open an issue.

## Conventions

- **One canonical skill per job.** No `-v2` or `-fix` variants; consolidate rather than fork.
- **Self-contained by rule.** A published `SKILL.md` carries everything it needs; it never routes
  to files that don't ship.
- **A skill is a checklist, not a manual.** Keep it scannable; push depth into clearly-named
  sections, not walls of prose.
