#!/usr/bin/env python3
"""Report overlapping paragraphs between different skills. Read-only, stdlib only.

Usage: skill_overlap.py ROOT [ROOT ...] [--threshold 0.85] [--min-words 8] [--within-skill]

ROOT is a plugin root (contains skills/), a skills root, or a single skill dir.
A skill is a directory holding SKILL.md; its files are SKILL.md plus references/**/*.md.
Paragraphs are normalised (lowercase, punctuation and whitespace folded) and compared
with difflib across DIFFERENT skills only. YAML frontmatter and fenced code blocks are
skipped: frontmatter is metadata unique to each skill, and code fences are examples
that legitimately repeat. Before comparing, each skill's own name (plugin:skill, or a
hyphenated bare name) and its own /plugin:skill command with its arguments are replaced by a
placeholder, so lines differing only by the skill naming itself match. The sentence holding
the command is the usage statement and is removed; a paragraph left with fewer than
--min-words words is dropped.
--within-skill also compares files of the SAME skill.
Exit 0 = no findings, 1 = findings, 2 = bad arguments.
"""
import argparse
import difflib
import re
import sys
from itertools import combinations
from pathlib import Path

DEFAULT_THRESHOLD = 0.85
DEFAULT_MIN_WORDS = 8
FENCE = re.compile(r'^\s*(```|~~~)')
PLACEHOLDER = 'skillname'


def name_patterns(name):
    """(command, mention) regexes for a skill naming itself.

    command: the plugin-qualified slash command /plugin:name with its arguments, either a
    backticked span (`/plugin:name <x> [args]`) or the command plus trailing <x>/[x] tokens.
    A bare /name is not a command (it is also a path or a word) and is not matched.
    mention: plugin:name, or a hyphenated bare name. Both are replaced by a placeholder so a
    copied paragraph that merely says which skill it sits in still matches. A one-word name
    such as `review` is an ordinary word and is only masked in the plugin:name form.
    """
    n = re.escape(name)
    q = r'/[\w.-]+:%s(?![\w-])' % n
    command = re.compile(r'`%s[^`]*`|%s(?:\s*(?:\[[^\]]*\]|<[^>]*>))*' % (q, q), re.IGNORECASE)
    prefixed = r'(?<![\w-])[\w.-]+:%s(?![\w-])' % n
    bare = r'(?<![\w-])%s(?![\w-])' % n
    mention = re.compile(bare if '-' in name else prefixed, re.IGNORECASE)
    return command, mention


def find_skills(root):
    """Directories under root (or root itself) that contain a SKILL.md."""
    root = Path(root)
    if (root / 'SKILL.md').is_file():
        return [root]
    return sorted(p.parent for p in root.rglob('SKILL.md'))


def skill_files(skill):
    files = [skill / 'SKILL.md']
    files += sorted((skill / 'references').rglob('*.md')) if (skill / 'references').is_dir() else []
    return files


def normalise(text):
    return ' '.join(re.sub(r'[^\w\s]', ' ', text.lower()).split())


def usage_stripped(text, own, min_words):
    """Mask the skill's own name in *text*; None when the paragraph is only a usage line.

    The sentence holding the skill's own command is the usage statement (the command, its
    arguments and what no argument does), which is one per skill by construction, so it is
    removed; the other sentences are real content and are compared. A paragraph left with
    fewer than *min_words* words is dropped.
    """
    text, n_cmd = own[0].subn(PLACEHOLDER, text)
    if n_cmd:
        keep = [x for x in re.split(r'(?<=[.!?])\s+', text) if PLACEHOLDER not in x]
        text = ' '.join(keep)
        if len(normalise(text).split()) < min_words:
            return None
    return own[1].sub(PLACEHOLDER, text)


def paragraphs(path, min_words, own_name=None):
    """Yield (start_line, normalised_text) for prose paragraphs, skipping frontmatter and fences.

    *own_name* (the skill's directory name) is replaced by a placeholder before normalising.
    """
    own = name_patterns(own_name) if own_name else None
    lines = path.read_text(encoding='utf-8').splitlines()
    i = 0
    if lines and lines[0].strip() == '---':
        i = next((n + 1 for n in range(1, len(lines)) if lines[n].strip() == '---'), 0)
    buf, start, in_fence = [], 0, False
    out = []

    def flush():
        if buf:
            joined = ' '.join(buf)
            if own:
                joined = usage_stripped(joined, own, min_words)
                if joined is None:
                    buf.clear()
                    return
            text = normalise(joined)
            if len(text.split()) >= min_words:
                out.append((start, text))
        buf.clear()

    for n in range(i, len(lines)):
        line = lines[n]
        if FENCE.match(line):
            flush()
            in_fence = not in_fence
        elif in_fence:
            continue
        elif not line.strip():
            flush()
        else:
            if not buf:
                start = n + 1
            buf.append(line)
    flush()
    return out


def collect(roots, min_words):
    seen, items = set(), []
    for root in roots:
        for skill in find_skills(root):
            if skill.resolve() in seen:
                continue
            seen.add(skill.resolve())
            for f in skill_files(skill):
                for line, text in paragraphs(f, min_words, skill.name):
                    items.append((skill.name, f, line, text))
    return items


def similarity(a, b, threshold=0.0):
    """Word-level similarity of two normalised paragraphs, 0.0 when it cannot reach *threshold*.

    Words, not characters, keep SequenceMatcher's sequences short; the length bound and the
    two quick ratios are cheap upper bounds, so most pairs never reach ratio().
    """
    if a == b:
        return 1.0
    wa, wb = a.split(), b.split()
    if not (wa and wb):
        return 0.0
    if 2 * min(len(wa), len(wb)) / (len(wa) + len(wb)) < threshold:
        return 0.0
    sm = difflib.SequenceMatcher(None, wa, wb, autojunk=False)
    if sm.real_quick_ratio() < threshold or sm.quick_ratio() < threshold:
        return 0.0
    return sm.ratio()


def find_overlaps(items, threshold, within_skill=False):
    found = []
    for a, b in combinations(items, 2):
        if a[0] == b[0] and not (within_skill and a[1] != b[1]):
            continue
        ratio = similarity(a[3], b[3], threshold)
        if ratio >= threshold:
            found.append((ratio, a, b))
    return sorted(found, key=lambda r: -r[0])


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('roots', nargs='+')
    ap.add_argument('--threshold', type=float, default=DEFAULT_THRESHOLD)
    ap.add_argument('--min-words', type=int, default=DEFAULT_MIN_WORDS)
    ap.add_argument('--within-skill', action='store_true',
                    help='also report overlaps between different files of the same skill')
    args = ap.parse_args(argv)
    missing = [r for r in args.roots if not Path(r).is_dir()]
    if missing or not 0 < args.threshold <= 1:
        print('error: bad root or threshold: %s' % (missing or args.threshold), file=sys.stderr)
        return 2
    items = collect(args.roots, args.min_words)
    found = find_overlaps(items, args.threshold, args.within_skill)
    for ratio, a, b in found:
        print('%.2f  %s:%d  <->  %s:%d' % (ratio, a[1], a[2], b[1], b[2]))
        print('      %s' % a[3][:100])
    print('%d finding(s) over %d paragraph(s), threshold %.2f' % (len(found), len(items), args.threshold))
    return 1 if found else 0


if __name__ == '__main__':
    sys.exit(main())
