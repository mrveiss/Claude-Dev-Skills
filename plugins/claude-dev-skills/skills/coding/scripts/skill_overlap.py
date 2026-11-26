#!/usr/bin/env python3
"""Report overlapping paragraphs between different skills. Read-only, stdlib only.

Usage: skill_overlap.py ROOT [ROOT ...] [--threshold 0.85] [--min-words 8]

ROOT is a plugin root (contains skills/), a skills root, or a single skill dir.
A skill is a directory holding SKILL.md; its files are SKILL.md plus references/**/*.md.
Paragraphs are normalised (lowercase, punctuation and whitespace folded) and compared
with difflib across DIFFERENT skills only. YAML frontmatter and fenced code blocks are
skipped: frontmatter is metadata unique to each skill, and code fences are examples
that legitimately repeat. Exit 0 = no findings, 1 = findings, 2 = bad arguments.
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


def paragraphs(path, min_words):
    """Yield (start_line, normalised_text) for prose paragraphs, skipping frontmatter and fences."""
    lines = path.read_text(encoding='utf-8').splitlines()
    i = 0
    if lines and lines[0].strip() == '---':
        i = next((n + 1 for n in range(1, len(lines)) if lines[n].strip() == '---'), 0)
    buf, start, in_fence = [], 0, False
    out = []

    def flush():
        if buf:
            text = normalise(' '.join(buf))
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
                for line, text in paragraphs(f, min_words):
                    items.append((skill.name, f, line, text))
    return items


def similarity(a, b):
    if a == b:
        return 1.0
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    if sm.quick_ratio() < 0.5:
        return 0.0
    return sm.ratio()


def find_overlaps(items, threshold):
    found = []
    for a, b in combinations(items, 2):
        if a[0] == b[0]:
            continue
        ratio = similarity(a[3], b[3])
        if ratio >= threshold:
            found.append((ratio, a, b))
    return sorted(found, key=lambda r: -r[0])


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('roots', nargs='+')
    ap.add_argument('--threshold', type=float, default=DEFAULT_THRESHOLD)
    ap.add_argument('--min-words', type=int, default=DEFAULT_MIN_WORDS)
    args = ap.parse_args(argv)
    missing = [r for r in args.roots if not Path(r).is_dir()]
    if missing or not 0 < args.threshold <= 1:
        print('error: bad root or threshold: %s' % (missing or args.threshold), file=sys.stderr)
        return 2
    items = collect(args.roots, args.min_words)
    found = find_overlaps(items, args.threshold)
    for ratio, a, b in found:
        print('%.2f  %s:%d  <->  %s:%d' % (ratio, a[1], a[2], b[1], b[2]))
        print('      %s' % a[3][:100])
    print('%d finding(s) over %d paragraph(s), threshold %.2f' % (len(found), len(items), args.threshold))
    return 1 if found else 0


if __name__ == '__main__':
    sys.exit(main())
