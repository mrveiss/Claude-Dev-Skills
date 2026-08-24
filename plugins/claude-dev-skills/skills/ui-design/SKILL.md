---
name: ui-design
description: Design, build, review, or polish any user interface — visual direction, typography, color, layout, spacing, motion, accessibility, responsive behaviour, theming, UX copy, empty and error states, and reusable design systems. Use for landing pages, dashboards, product UI, app shells, components, forms, onboarding, and redesigns; also for making a bland design bolder, a loud one quieter, or auditing an existing interface. Not for backend-only work.
---

# UI Design

One skill for every interface job. It replaced five overlapping ones — the source material for
each is carried whole in `references/`, so reach for the reference the task actually needs
instead of reading everything.

## Route first

| The job in front of you | Read |
|---|---|
| Picking an aesthetic direction; the design must not look templated | `references/visual-direction.md` |
| Reviewing or auditing an existing UI — hierarchy, IA, a11y, perf, i18n, anti-patterns | `references/audit-and-review.md` |
| A landing page, portfolio, or redesign that must not read as generic | `references/anti-slop-and-redesign.md` |
| Component polish, micro-interactions, animation, the invisible details | `references/polish-and-motion.md` |
| Design systems, tokens, per-stack idioms (React, Vue, Tailwind, shadcn, SwiftUI, Flutter…) | `references/systems-and-stacks.md` |
| A concrete palette, font pairing, chart type, or product archetype | `references/lookup/*.csv` |

`references/lookup/` holds the data tables: `colors.csv`, `typography.csv`, `google-fonts.csv`,
`styles.csv`, `products.csv`, `charts.csv`, `icons.csv`, `ux-guidelines.csv`, `landing.csv`,
`app-interface.csv`, `ui-reasoning.csv`, `react-performance.csv`, and `stacks/`. Grep the table;
never read a whole CSV into context.

## Non-negotiable

The project's own conventions win over anything a reference file says — read them first, then:

- **No hardcoded UI strings.** Route every user-facing string through the project's i18n layer,
  in every configured locale — no exceptions.
- **No stray `console.*`.** Use the project's logger.
- **Config through the project's single source of truth** — no hardcoded URLs, IPs, or ports.
- **One canonical name.** No `Enhanced`/`Unified`/`V2` prefixes on components or composables.
- **Reuse before creating.** Check the shared component/token kit before adding to it.
- **Run every linter the project runs**, not just one — a second linter can fail what the first
  passed.
- **Theme both directions.** Tokens on bare `:root`; redefine under
  `@media (prefers-color-scheme: dark)` guarded as `:root:not([data-theme="light"])`, and again
  under `:root[data-theme="dark"]`. A color defined only inside a media or `[data-theme]` block
  is the classic unreadable-page bug.

## Order of work

1. **Read the brief for treatment, not for whether to design.** A memo and a landing page get the
   same craft, delivered differently. Over-designing a utilitarian page is the common failure.
2. **Honor what exists.** An existing token file, theme, or component kit outranks your taste.
   Precedence: the user's words → the project's system → your choices.
3. **On a redesign, audit before touching.** Name what is actually wrong — hierarchy, density,
   contrast, rhythm — before proposing a look. `references/audit-and-review.md` carries the checklist.
4. **Plan the tokens before the markup.** 4–6 named colors, 2+ typefaces with real fallback
   stacks, one type scale, one layout concept. Derive every later decision from that plan.
5. **Build, then verify against the plan.** Spacing via flex/grid `gap`, wide content in its own
   `overflow-x:auto` container, visible focus states, `prefers-reduced-motion` respected.

## Avoid the generated look

Warm cream with a serif and terracotta accent · near-black with one acid-green pop · a
purple-to-blue gradient hero · Inter or Space Grotesk as the safe face · emoji as section
markers · everything centered · `rounded-lg` on everything · an accent rail on every card.
Where the user names a direction, follow it exactly — including when it is one of these.

## Done means

- [ ] Treatment matches the brief; nothing over-designed
- [ ] Existing design system honored, not overridden
- [ ] Both themes resolve; no color defined only behind a media or `[data-theme]` block
- [ ] Every string i18n'd in all configured locales; no stray logging; no hardcoded config
- [ ] Every linter the project runs is clean, not just one
- [ ] Wide content scrolls in its own container; focus visible; reduced-motion respected

## Credits

Consolidates and adapts five design skills: Emil Kowalski's UI polish/motion philosophy,
Anthropic's frontend-design, and the ui-ux-pro-max, taste-skill, and impeccable skills. The
routing above is original; the adapted reference material is local-only and not redistributed.
