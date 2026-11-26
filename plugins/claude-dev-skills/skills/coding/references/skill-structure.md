When to use: Writing, splitting, merging or reviewing a skill; two skills say the same thing; deciding whether a new skill or a meta-skill is needed.

# /claude-dev-skills:coding skill-structure — One job per skill, one home per subject

Skills follow the same library structure as memory: a subject has exactly one home. Owner rule (2026-11-26).

## The rules

1. **One job per skill.** Each skill does one unique job. If you cannot state the job in one sentence without "and", split it.
2. **Shared content has exactly one home skill.** When part of one skill becomes similar to part of another, the shared part is not kept in both. Pick the skill whose job it is, keep it there, and make the other skill link to it. Duplicated text drifts, and the model cannot tell which copy is current.
3. **A meta-skill composes two or more skills.** It links to them and says how and in what order (and under what conditions) to use them. It never copies their instructions.

Owner's example: the skills are *operate a table saw*, *use measuring instruments*, *read furniture designs*, *glue pieces together*, *screw pieces together*. The meta-skill *build furniture* says which of those to use, how, and in what order: read the design, measure, cut on the saw, then glue or screw. It does not explain how to run a saw.

## Router skill vs meta-skill

| | Router skill | Meta-skill |
|---|---|---|
| Links to | only its own `references/` | two or more other skills |
| Job | one subject; picks which reference to read | one outcome that needs several subjects |
| Content | a routing table plus rules that hold without loading a reference | order, conditions and hand-off between skills; no copied instructions |

A SKILL.md that links only to its own `references/` is a **router skill**, not a meta-skill. Every skill in this plugin is a router skill today. Calling a router a meta-skill is retired wording; do not use it.

## Resolving an overlap

Run the checker (read-only, stdlib only):

```bash
python3 <plugin>/skills/coding/scripts/skill_overlap.py <plugin-or-skills-root> [<root> ...] [--threshold 0.85]
```

It normalises paragraphs (frontmatter and code fences skipped; case, punctuation and whitespace folded) and reports pairs from different skills at or above the threshold, with `file:line` on both sides. Paragraphs under 8 words are ignored. For each finding:

1. **Decide the home** by asking which skill's job the passage is. The home keeps the text.
2. **Replace the other copy with a link** to the home reference, plus at most one sentence of context.
3. **Used together in a fixed order?** Only then add a meta-skill that links the skills and states the order. Do not add one for a mere cross-reference.
4. **Not a real overlap?** (a shared boilerplate line, a quoted rule that is deliberately resident in a router) record it as a false positive with the reason; do not reword it to dodge the checker.
5. Re-run until the report is empty or every remaining finding is a documented false positive.
