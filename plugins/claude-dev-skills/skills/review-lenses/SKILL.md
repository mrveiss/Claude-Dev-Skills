---
name: review-lenses
description: Domain review lenses — architecture, delivery, frontend, documentation, UX, and visual craft. Use for any review task where the question is "is this good?" rather than "does it run?". Pair with the project's own review process docs, which cover mechanics (dispatch, gates, merge).
---

# Review Lenses

Process docs tell you *how* to run a review. These lenses tell you *what to judge*. Apply the ones relevant to the change and cite each by name so the reasoning is traceable.

Project-specific facts (stack versions, known gotchas, house conventions) live in the project's CLAUDE.md — not here.

---

## Architecture

- **Blast radius** — how far does this propagate if it fails? Can it be scoped, gated, or rolled back?
- **Incremental over big-bang** — prefer additive changes and strangler-fig migration to rewrites; migrate live systems in place.
- **Boring technology** — the most boring thing that works. Spend novelty budget only on core competitive edges.
- **Build vs buy vs integrate** — make (control), buy (lock-in), integrate (support burden). Name which one and why.
- **API contract stability** — public and inter-service APIs are contracts; breaking one propagates cost downstream.
- **Observability before load-bearing** — metrics, logs, and traces ship *with* the feature, not after it matters.
- **Dependency surface** — every dependency is a permanent maintenance liability. Require justification.
- **Failure mode clarity** — for each integration point, name the failure mode and the fallback path.
- **Security by design** — authn/authz, least privilege, secrets handling, and input validation are architecture, not polish.
- **Conway's Law** — the architecture will mirror the team structure. Structure the team to get the system you want.

## Delivery

- **WIP limit** — throughput is finite. Three-plus things in flight for one owner means one should be deferred.
- **Critical path** — the chain gating the next user-visible outcome. Protect it; reorder everything else around it.
- **Reversibility** — two-way doors (easy revert) ship now; one-way doors (data shape, auth, billing) get a confirmation step.
- **Acceptance clarity** — an item without a "you'll know it's done when…" line is a backlog note, not a task. Push back before starting.
- **Blocker honesty** — "waiting on review" is not a blocker if no one was asked. Convert vague waits into named asks.
- **Coordination tax** — every status sync costs someone's attention. Fewer, denser updates; never ping without a concrete ask.

## Frontend (Vue 3 + TypeScript)

1. **Composition API purity** — `ref`, `reactive`, `computed`, `watch`, composables. Options API in new code is a bug.
2. **Type soundness** — derive types from schemas or validators; no `any`/`unknown` without a narrowing guard.
3. **Import discipline** — the project's alias for intra-project imports; no reaching into sibling internals; no barrel-over-barrel re-exports.
4. **Store contract** — single-responsibility state machines; no business logic outside actions; no external `.state` mutation.
5. **Story before ship** — a component without a Story is not done.
6. **Component contract** — props and emits fully typed, `v-model` wired correctly, no implicit prop drilling past one level.
7. **Colocated tests** — test beside the component; mock only external boundaries, never code you own.
8. **HTTP envelope awareness** — know whether the client returns parsed data or a response object. Reaching for `response.data.X` on a client that already parses is a bug, and it is a recurring one.
9. **Performance baseline** — stable `:key` on every `v-for`; virtual scroll for large lists; no gratuitous reactive wrapping.
10. **Accessibility baseline** — semantic HTML first, ARIA only where semantics fall short, focus management in modals, contrast checked before handoff.

## Documentation

1. **Accessible** — readable without assumed context; jargon defined on first use.
2. **Accurate** — every command, path, and API call works against the current code. No stale references.
3. **Complete both ways** — a feature in code is documented; a feature in docs exists in code.
4. **Discoverable** — reachable via README links, cross-references, or obvious structure.
5. **Consistent** — one vocabulary and one shape across the doc set.
6. **Reproducible** — examples run end to end, including setup and expected output.
7. **Link integrity** — internal references resolve to current files and anchors.
8. **Single source of truth** — each fact lives in exactly one place; link rather than duplicate.
9. **Progressive disclosure** — simplest case first, advanced options layered after.
10. **Ages well** — avoid documenting implementation details that churn.

## UX

- **Cognition** — cognitive load, working memory, chunking, mental models, aesthetic-usability effect.
- **Gestalt** — proximity, similarity, common region, uniform connectedness, Prägnanz.
- **Decision & attention** — Hick's Law, choice overload, Fitts's Law, serial position, Von Restorff, peak-end, goal-gradient.
- **System behavior** — Doherty threshold (<400 ms), Jakob's Law, Tesler's Law, Postel's Law, Occam's razor, Pareto.
- **Heuristics** — Nielsen's 10, Shneiderman's 8, Norman's affordances / signifiers / feedback / mapping / constraints, recognition over recall.
- **Behavioral** — loss aversion, anchoring, social proof, defaults, framing, commitment and consistency.
- **Accessibility** — WCAG POUR, contrast, colour-independence, target size, timeouts, reading level, reduced motion.
- **IA & content** — information scent, F/Z scanning patterns, inverted pyramid, plain language.
- **Forms & errors** — forgiveness (undo, confirm destructive, recover), inline validation, single-column layout.
- **Motion & perceived performance** — purposeful animation, ~100 ms feedback, skeletons and optimistic UI.
- **Ethics** — refuse dark patterns. Persuasion is not manipulation. Never auto-send without explicit, reversible consent.

## Visual Quality Bar

A functional UI is not a finished UI.

- **Hierarchy is visible** — a stranger names primary/secondary/tertiary in two seconds. Equal weight everywhere means no emphasis anywhere.
- **Spacing is intentional** — from the scale. No stray gaps, nothing touching edges, nothing crammed against a sibling.
- **Alignment is ruthless** — to a grid, a baseline, or a shared edge. Nothing floats.
- **Type has a system** — sizes, weights, line-heights come from the scale, not picked per component.
- **Density matches context** — dashboards can be dense, forms need room.
- **Defaults are polished** — empty, loading, and error states get the same care as the happy path.

If a screen looks like raw HTML, say so and fix it. Correct flow is not a reason to ship it.

## Visual Truth Gate (mandatory for UI-visible changes)

A verdict on a UI-visible change requires that you **rendered the surface at a real viewport in this run**. Diff plus spec inspection is PR review, not UX review.

Before approving or requesting changes, pick one:

1. **Open it** — dev server or preview URL at desktop and mobile viewports (default 1440×900 / 390×844). Name surface and viewport in the comment; attach a screenshot when the review is about visual craft.
2. **Require evidence** — handed off without screenshots? Send it back: "post 1440×900 and 390×844 screenshots, or a preview URL, before re-review."
3. **Scope explicitly** — if only part is renderable, state which states you verified, block the rest on a named sibling issue, and mark the work in-review — not done.

"Pixel review deferred to QA" is not a UX pass.

---

## Which lenses to apply

| Change type | Lenses |
|---|---|
| Backend / architecture | Architecture + Delivery |
| Frontend code | Frontend + Delivery |
| UI-visible change | Visual Truth Gate → Visual Quality Bar → UX |
| Documentation | Documentation |
| Full PR review | Architecture + Delivery + relevant domain lenses |
