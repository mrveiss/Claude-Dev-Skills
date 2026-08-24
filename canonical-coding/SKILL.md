---
name: canonical-coding
description: The canonical-source discipline for ALL code changes in this repository. Use this skill whenever writing, modifying, reviewing, or planning ANY code — frontend, backend, infra, migrations, or docs that describe code. Especially use it when tempted to create a new helper, wrapper, framework, endpoint, config, schema bootstrap, or "v2" of anything that already exists; when a frontend and backend disagree; when a plan or doc disagrees with the code; or when two implementations of the same concept are found. This skill defines which source wins every conflict.
---

# Canonical Coding

One concept, one authoritative implementation, one source of truth — and a
defined winner for every conflict. Most defects in this codebase have been
violations of this rule: GUIs written against imagined APIs, a hook framework
existing twice, schema created by two competing mechanisms, docs describing a
product that doesn't exist, a license swapped by a session that thought it was
helping.

## The hierarchy of truth (who wins every disagreement)

1. **Running code with passing tests** beats everything below.
2. **The backend contract** beats the frontend's expectations.
   Frontend conforms to `openapi.json`; it never invents paths. If the
   endpoint doesn't exist, the backend route is built FIRST, the spec is
   re-dumped, types regenerated — then the frontend call is written.
3. **Migrations** beat ORM bootstrap. Alembic is the only schema authority
   in production; `metadata.create_all` is a gated dev convenience, never a
   parallel schema mechanism.
4. **Generated artifacts** beat hand-written duplicates.
   Types come from `src/types/generated/api.ts`; if the generated file lacks
   what you need, that IS the contract check failing — fix upstream and
   regenerate, never hand-type around it.
5. **Code** beats plans, PRDs, issues, and docs. A plan saying "implemented"
   proves nothing; verify in the tree. Docs describing capabilities are
   claims to be checked, not facts to build on.
6. **The human** beats the agent for: product decisions, licensing
   (LICENSE/NOTICE/SPDX are READ-ONLY), umbrella/epic lifecycle, merges,
   ADR amnesty. When a fix requires a decision from this list, STOP and ask.

## The prime directive: extend, never fork

Before writing ANY new function, class, endpoint, config block, or framework:

1. **Search for the existing implementation first.** Grep for the concept,
   not just the name (the thing you need may exist under another name —
   "routines" was the heartbeat scheduler; org-chart data lived in
   companies + agent_hires).
2. **If it exists: extend it or fix it in place.** A wrapper around a broken
   thing, a parallel "clean" version, or a copy-with-tweaks is a fork —
   forks are how this repo got two hook frameworks and 1,800 duplicated
   lines.
3. **If it exists but is wrong: fix it where it lives**, behind its existing
   interface, with a red-first test. Callers should not know it changed.
4. **If it truly doesn't exist: build it once, in the layer that owns the
   concept**, and wire every consumer to it. Shared logic goes where both
   consumers can reach it — not copied into each.
5. **If two implementations already exist: do not write a third.** Determine
   which is canonical (git history, live imports, tests), migrate consumers
   to it, and reduce the other to a re-export shim or delete it. When the
   "fork" is actually an unfinished rename, finish the rename.

## Beware the wrong abstraction

Duplication is cheaper than the wrong abstraction. Do NOT unify two things
merely because they look alike — unify them because they ARE the same concept
with the same reasons to change. If extraction would couple unrelated domains,
skip it and document why. Never create `utils/common`-style god-modules.

## Mechanical enforcement (run these; do not self-certify)

- API contract: `python scripts/audit_api_wiring.py --openapi openapi.json
  --fail-on-unwired` — must exit 0 for the surface you touched.
- Duplication: the CI duplication guard threshold must not grow; if your
  change adds a clone, you forked something — find the canonical home.
- New FastAPI router modules are registered in the router registry IN THE
  SAME COMMIT. An unregistered router is a defect, not a draft.
- Schema changes ship as Alembic revisions with upgrade+downgrade; never as
  model edits relying on create_all.
- Before final push: `grep -rn "^<<<<<<< " --include="*"` must be empty.
- Shared state (umbrella task lists, MOC indexes, handoff files) is
  append/edit-in-place — never rewritten wholesale.
- Reference epics with "part of #N", never closing keywords.

## Smells that mean you are about to violate this skill

- "I'll just write a quick local version of..."        → search first.
- "The existing one is messy, I'll make a clean one."  → fix in place.
- "The doc/issue says the endpoint exists."            → verify in code.
- "I'll hardcode it for now."                          → env/config, or stop.
- "I'll also clean up this unrelated thing."           → out of scope; file
  an issue instead.
- "This license/header looks outdated."                → READ-ONLY; flag it.

## When canon itself must change

Changing what is canonical (replacing a framework, moving an authority,
re-drawing a module boundary) is an architecture decision: propose it in the
PR/report with the migration path, get the human's explicit approval, and
record it as an ADR. Until approved, the old canon stands and your change
conforms to it.
