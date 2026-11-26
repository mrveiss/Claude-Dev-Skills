#!/usr/bin/env python3
"""PreToolUse hook (matcher: Write): block a NEW memory fact file lacking author:/created:.

Reads the hook JSON on stdin. Exit 2 + stderr blocks the call (Claude Code hooks reference,
"Exit code 2"); anything else lets it through. The memory dir is detected from the path
pattern <...>/.claude/projects/<project>/memory/, never hard-coded.
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _lib  # noqa: E402

MEMORY_PATH = re.compile(r'^(?P<mem>.*/\.claude/projects/[^/]+/memory)/(?P<rel>.+)$')
EXEMPT_TOP = ('topics', 'library')
DATE = re.compile(r'^\d{4}-\d{2}-\d{2}$')


def is_fact_path(path):
    """True for a non-exempt .md file under a memory dir."""
    m = MEMORY_PATH.match(path.replace(os.sep, '/'))
    if not m or not m.group('rel').endswith('.md'):
        return False
    rel = m.group('rel')
    return rel != 'MEMORY.md' and rel.split('/')[0] not in EXEMPT_TOP


def problems(content):
    fm = _lib.parse_frontmatter(content)
    found = []
    if not fm.get('author'):
        found.append('author: <who wrote it: "owner" for a rule the owner stated, else your session name>')
    if not DATE.match(fm.get('created', '')):
        found.append('created: <YYYY-MM-DD, today>')
    return found


def message(path, missing):
    return ('Blocked: new memory fact file without required metadata: ' + path + '\n'
            'Add these keys under `metadata:` in the frontmatter, then write again:\n'
            + ''.join(f'  {m}\n' for m in missing)
            + 'Example:\n---\nname: ...\ndescription: ...\nmetadata:\n  type: feedback\n'
              '  author: owner\n  created: 2026-01-31\n---\n'
            'File times are not creation dates, so the date must be written in the file.')


def main():
    try:
        data = json.load(sys.stdin)
    except ValueError:
        return 0
    if data.get('tool_name') != 'Write':
        return 0
    inp = data.get('tool_input') or {}
    path = inp.get('file_path') or ''
    if not is_fact_path(path) or os.path.exists(path):
        return 0
    missing = problems(inp.get('content') or '')
    if not missing:
        return 0
    sys.stderr.write(message(path, missing))
    return 2


if __name__ == '__main__':
    sys.exit(main())
