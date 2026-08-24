---
name: ui-design
description: Design, build, review, or polish any user interface — visual direction, typography, color, layout, spacing, motion, accessibility, responsive behaviour, theming, UX copy, empty and error states, and reusable design systems. Use for landing pages, dashboards, product UI, app shells, components, forms, onboarding, and redesigns; also for making a bland design bolder, a loud one quieter, or auditing an existing interface. Not for backend-only work.
---

# UI Design

One skill for every interface job — visual direction, review, redesign, polish, and design
systems, self-contained below.

## Pick the lens the task needs

**Aesthetic direction (the design must not look templated).** Work in two passes: first a short
written plan — 4–6 named colors, two typefaces with real fallback stacks, one type scale, one
layout idea, all specific to *this* subject; then build from it. The hero is a thesis: open with
the most characteristic thing in the subject's world, not a generic banner. Spend boldness in one
place and keep everything around it quiet.

**Reviewing or auditing an existing UI.** Name what is actually wrong before proposing a look:
visual hierarchy (does the eye land where it should?), information architecture, cognitive load,
contrast and legibility, spacing rhythm, alignment, responsive behaviour, accessibility (focus
order, contrast ratios, reduced-motion), and i18n. Produce findings ranked by impact, not a
restyle.

**A landing page, portfolio, or redesign that must not read as generic.** Infer the right
direction from the brief instead of reaching for the safe default. On a redesign, audit first
(above), then commit to one opinionated direction and execute it precisely — minimal directions
need precision in spacing and type; maximalist ones need elaborate, consistent execution.

**Component polish and motion — the invisible details.** Animate deliberately: a load sequence, a
scroll reveal, a hover micro-interaction, or ambient atmosphere — one orchestrated moment beats
scattered effects, and too much motion reads as generated. Respect `prefers-reduced-motion`. Mind
the details that make software feel finished: optical alignment, consistent easing, states for
hover/active/focus/disabled/loading/empty/error.

**Design systems and per-stack idioms.** Define tokens (color, type, space, radius, shadow) once
and style through them, never with literals. Match the target stack's idioms — React/Vue
components, Tailwind utilities, shadcn primitives, SwiftUI/Flutter widgets — rather than porting
one framework's patterns into another.

**Concrete palettes, font pairings, chart types.** Choose neutrals with a slight hue bias toward
the accent rather than a dead grey. Keep running text near 65 characters wide. For data, give
charts the same care as type — an area fill, a faint grid, an emphasized endpoint; semantic
good/warning/critical color is separate from the brand accent.

## Non-negotiable

The project's own conventions win over anything here — read them first, then:

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
   contrast, rhythm — before proposing a look, using the review lens above.
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
guidance above is an original, self-contained rewrite; the source skills' material is not redistributed here.
