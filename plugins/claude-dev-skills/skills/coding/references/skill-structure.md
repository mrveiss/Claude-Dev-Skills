When to use: Writing, splitting, merging or reviewing a skill; two skills say the same thing; deciding whether a new skill or a meta-skill is needed.

# /claude-dev-skills:coding skill-structure — One job per skill, one home per subject

Skills follow the same library structure as memory: a subject has exactly one home. Owner rule (2026-11-26).

## The rules

1. **One job per skill.** Each skill does one unique job. If you cannot state the job in one sentence without "and", split it.
2. **Shared content has exactly one home skill.** When part of one skill becomes similar to part of another, the shared part is not kept in both. Pick the skill whose job it is, keep it there, and make the other skill link to it. Duplicated text drifts, and the model cannot tell which copy is current.
3. **A meta-skill composes two or more skills.** It links to them and says how and in what order (and under what conditions) to use them. It never copies their instructions.
4. **An agent is the specialist who knows which skill to use and when.** It holds no skill content: it names the skill or meta-skill to use for each condition, plus its tools and model. Where an agent definition contains skill instructions, move them to the home skill (rule 2) and leave a "use `<skill>` when `<condition>`" line in the agent. Owner rule (2026-11-26).

Owner's example: the skills are *operate a table saw*, *use measuring instruments*, *read furniture designs*, *glue pieces together*, *screw pieces together*. The meta-skill *build furniture* says which of those to use, how, and in what order: read the design, measure, cut on the saw, then glue or screw. It does not explain how to run a saw. The agents are the carpenters: the *carpenter* agent (tools, model) knows to use *build furniture* when asked for a cabinet and *operate a table saw* when asked only to cut a board; it holds neither skill's steps.

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
python3 <plugin>/skills/coding/scripts/skill_overlap.py <plugin-or-skills-root> [<root> ...] [--threshold 0.85] [--within-skill]
```

It normalises paragraphs (frontmatter and code fences skipped; case, punctuation and whitespace folded) and reports pairs from different skills at or above the threshold, with `file:line` on both sides. Paragraphs under 8 words are ignored. A skill's own name (`plugin:skill`, or a hyphenated bare name) is masked before comparing; the sentence holding its own `/plugin:skill` command (a bare `/name` is not a command) is its usage statement and is removed, and a paragraph left under 8 words is dropped, so a skill naming itself is never a finding while a real rule next to the command still is. `--within-skill` (opt-in) also compares different files of the same skill (SKILL.md vs a reference, reference vs reference). For each finding:

1. **Decide the home** by asking which skill's job the passage is. The home keeps the text.
2. **Replace the other copy with a link** to the home reference, plus at most one sentence of context.
3. **Used together in a fixed order?** Only then add a meta-skill that links the skills and states the order. Do not add one for a mere cross-reference.
4. **Not a real overlap?** (a shared boilerplate line, a quoted rule that is deliberately resident in a router) record it as a false positive with the reason; do not reword it to dodge the checker.
5. Re-run until the report is empty or every remaining finding is a documented false positive.
