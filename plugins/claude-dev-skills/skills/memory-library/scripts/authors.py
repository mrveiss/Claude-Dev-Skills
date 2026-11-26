#!/usr/bin/env python3
"""Attribute facts to an author; write <memory-dir>/library/authors.json.

usage: python3 -I authors.py <memory-dir>

Output is {fact: {author, source}}. Sources, in order: `frontmatter` (author:), `ledger` (the
ledger name recorded for the fact's originSessionId), else `unresolved` (author `unrecorded`).
Only a recorded mapping is used; an author is never guessed from text or a file name.
The ledger is optional: `ledger_cmd` in classes.json (or env MEMORY_LIBRARY_LEDGER, which wins)
names its command; `<cmd> sessions` maps name -> sid. Without it every unattributed fact stays
unrecorded and the run says so. Never edits a fact file.
"""
import collections
import json
import os
import re
import shlex
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _lib  # noqa: E402

# `ledger sessions` row: name, liveness text, then the `sid <hex>` column (two or more spaces before it)
ROW_RE = re.compile(r'^(\S+)\s+(?:(?!\bsid\b).)*?\s{2,}sid\s+([0-9a-f]{8,})(?=\s|$)')
UNSAFE_CMD_RE = re.compile(r'[;|&<>$`\\"\'(){}*?!#\[\]\n]')
MIN_SID = 8  # a recorded sid prefix shorter than this is not distinctive enough to match on


def ledger_sessions(cfg, notes):
    """[(name, sid)] from `<ledger_cmd> sessions`, or None (with the reason in notes) when no ledger answers."""
    cmd = os.environ.get('MEMORY_LIBRARY_LEDGER', cfg.get('ledger_cmd'))
    if cmd is None or (cmd == '' and 'MEMORY_LIBRARY_LEDGER' not in os.environ and 'ledger_cmd' not in cfg):
        notes.append('no ledger configured (ledger_cmd in classes.json): sessions are not resolved')
        return None
    if not cmd.strip() or UNSAFE_CMD_RE.search(cmd):
        _lib.die(f'ledger_cmd {cmd!r} must be a plain command or path (no shell metacharacters); see references/classification.md')
    argv = shlex.split(os.path.expanduser(cmd))
    if not argv or not shutil.which(argv[0]):
        notes.append(f'ledger command {argv[0] if argv else cmd!r} not found: sessions are not resolved')
        return None
    try:
        done = subprocess.run(argv + ['sessions'], capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired):
        done = None
    if done is None or done.returncode != 0:
        notes.append('ledger sessions failed: sessions are not resolved')
        return None
    rows = [m.groups() for m in map(ROW_RE.match, done.stdout.splitlines()) if m]
    return [(name, sid) for name, sid in rows if len(sid) >= MIN_SID]


def ledger_name(rows, origin):
    """The one ledger name whose recorded sid is (a prefix of) origin; None when none or several match."""
    names = {name for name, sid in rows if origin.startswith(sid)}
    return names.pop() if len(names) == 1 else None


def resolve(mem, cfg, rows):
    table = {}
    for fact in sorted(f for f in _lib.source_lines(mem, cfg) if f):  # external entries are not facts
        fm = _lib.frontmatter(os.path.join(mem, fact))
        name = ledger_name(rows or [], fm['originSessionId']) if fm.get('originSessionId') else None
        if fm.get('author'):
            table[fact] = {'author': fm['author'], 'source': 'frontmatter'}
        elif name:
            table[fact] = {'author': name, 'source': 'ledger'}
        else:
            table[fact] = {'author': _lib.UNRECORDED, 'source': 'unresolved'}
    return table


def main(argv):
    if len(argv) != 2:
        _lib.die(__doc__)
    mem = os.path.abspath(argv[1])
    cfg = _lib.load_classes(mem)
    notes = []
    table = resolve(mem, cfg, ledger_sessions(cfg, notes))
    _lib.write_text(mem, os.path.join(mem, 'library', _lib.AUTHORS_FILE),
                    json.dumps(table, indent=1, sort_keys=True, ensure_ascii=False) + '\n')
    for note in notes:
        print('authors: ' + note)
    counts = collections.Counter(e['source'] for e in table.values())
    print(f'authors: {len(table)} facts; ' + ', '.join(f'{s} {n}' for s, n in sorted(counts.items())))


if __name__ == '__main__':
    main(sys.argv)
