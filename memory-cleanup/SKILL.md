---
name: memory-cleanup
description: End-of-session memory hygiene ritual. Run this at the end of every session to keep MEMORY.md an index and every memory reachable from a topic file.
---

# /memory-cleanup — Session-End Memory Hygiene

Run at the end of every work session. Takes ~2 minutes.

Memory is **hub and spoke**: `MEMORY.md` is an index (always resident),
`topics/<topic>.md` are per-topic indexes (loaded on demand), and each fact lives
in its own file. Cleanup keeps that shape — it does not inline facts back into
the hub.

## Step 0: Resolve the memory directory (machine-agnostic)

Use the memory directory stated in THIS session's system prompt (the `# Memory`
section names it). Never hardcode a machine-specific path:

```bash
MEM=<memory directory from the system prompt>   # e.g. ~/.claude/projects/<project-slug>/memory
```

## Step 1: Check the hub's size

```bash
wc -c "$MEM/MEMORY.md"
```

Target: **under 7000 chars**. Over that means facts have leaked into the hub —
go to Step 4.

## Step 2: File this session's new memories

For each fact worth keeping:

1. Write it to its own file with `name` / `description` / `metadata.type`
   frontmatter (`user` | `feedback` | `project` | `reference`).
2. Add a one-line pointer to the matching `topics/*.md`:
   `- [title](../file.md) — hook`
3. Only touch `MEMORY.md` if the rule is safety-critical (see Step 5).

## Step 3: Verify Open Work

For each issue under `## Open Work` in MEMORY.md:

```bash
gh issue view <number> --json state,title -q '"\(.state) \(.title)"'
```

- **CLOSED** → remove the line; the detail file moves to `topics/recent-work.md`.
- **OPEN** → leave it; refresh the hook if it changed.

> If `gh` errors (no auth/network), skip this step rather than guessing.

## Step 4: Keep the hub an index

Scan `MEMORY.md` for lines that carry a *fact* rather than a *pointer* — a
GOTCHA, a command, a version, an explanation. For each:

1. Confirm the fact already exists in its linked file
   (`grep -i '<keyword>' "$MEM/<file>.md"`).
2. **If it is missing, append it to that file FIRST.** Never trim the hub before
   the fact is safe somewhere else.
3. Then reduce the hub line to `- [title](file.md) — ≤100-char hook`.

## Step 5: Check reachability and residency

```bash
cd "$MEM"
# every memory reachable from the hub or a topic index?
for f in *.md; do case "$f" in MEMORY.md|MEMORY.md.bak*) continue;; esac
  grep -q "($f)" MEMORY.md && continue
  grep -qr "(\.\./$f)" topics/ && continue
  echo "UNREACHABLE $f"
done
# no dangling links?
for l in $(grep -oP '\]\(\K[^)]+' MEMORY.md); do [ -e "$l" ] || echo "BROKEN $l"; done
```

An unreachable memory is invisible to recall — that is how a documented gotcha
gets rediscovered the hard way. Fix every hit.

**Residency rule:** a rule stays in `MEMORY.md`'s *Always Apply* section only if
missing it causes damage that is hard to undo — data loss, wrong attribution,
pushing to a protected branch, destroying another session's work, leaking
internal details outward. Everything else belongs in a topic index. Do not grow
*Always Apply* for convenience.

## Step 6: Age out episodic records

Session, umbrella, epic, and loop records older than ~30 days move from
`topics/recent-work.md` to `topics/archive.md`. The files themselves stay on
disk — only the index line moves.

## Step 7: Report

```bash
wc -c "$MEM/MEMORY.md"
```

Announce: "Memory cleanup complete. MEMORY.md is N chars; X memories filed, Y
aged out, 0 unreachable."
