#!/usr/bin/env python3
"""Date every fact with the certainty its source gives; write <memory-dir>/library/dates.json.

usage: python3 -I dates.py <memory-dir>

Precedence per fact: created: (exact) -> a date in the entry (exact) -> originSessionId's
session start (near-exact) -> cited issue/PR #N (not-before, with modified: as not-after)
-> file time (approximate; a bulk-copy day is unknown) -> unknown. Output is
{fact: {date, source, quality, ...}}. Entries linking to a URL are not facts and get no row. Never edits a fact file. Issue/PR dates come from
batched `gh api graphql` queries for the `github_repo` in classes.json, cached in library/ref-dates.json.
Day boundaries use `timezone` (IANA name) from classes.json, else the machine's local zone.
Env MEMORY_LIBRARY_HOME replaces the home directory (session transcripts, history.jsonl).
"""
import collections
import datetime
import glob
import json
import os
import re
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _lib  # noqa: E402

BATCH = 50  # issueOrPullRequest fields per GraphQL query
REPO_RE = re.compile(r'^[\w.-]+/[\w.-]+$')
TS_RE = re.compile(r'"timestamp":\s*"([^"]+)"')


def claude_dir():
    return os.path.join(os.environ.get('MEMORY_LIBRARY_HOME') or os.path.expanduser('~'), '.claude')


def iso_day(stamp):
    if not stamp:
        return None
    # pad fractional seconds to 6 digits: older Pythons parse only 3 or 6
    stamp = re.sub(r'\.(\d{1,6})', lambda m: '.' + m.group(1).ljust(6, '0'), stamp.replace('Z', '+00:00'), count=1)
    try:
        when = datetime.datetime.fromisoformat(stamp)
    except ValueError:
        return None
    return when.astimezone(datetime.timezone.utc)


def earliest(stamps, tz):
    days = [d for d in stamps if d]
    return _lib.day_of(min(days), tz) if days else None


def transcript_stamps(sid):
    for path in glob.glob(os.path.join(claude_dir(), 'projects', '*', f'{glob.escape(sid)}.jsonl')):
        with open(path, encoding='utf-8', errors='replace') as fh:
            for line in fh:
                m = TS_RE.search(line)
                if m:
                    yield iso_day(m.group(1))


def history_stamps(sid):
    path = os.path.join(claude_dir(), 'history.jsonl')
    if not os.path.isfile(path):
        return
    with open(path, encoding='utf-8', errors='replace') as fh:
        for line in fh:
            if sid not in line:
                continue
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            if rec.get('sessionId') == sid and isinstance(rec.get('timestamp'), (int, float)):
                yield datetime.datetime.fromtimestamp(rec['timestamp'] / 1000, datetime.timezone.utc)


def session_date(sid, tz):
    """Start day (in tz) of a session: transcript first, else history.jsonl; None when neither knows it."""
    return earliest(transcript_stamps(sid), tz) or earliest(history_stamps(sid), tz)


class RefDates:
    """Issue/PR creation dates via `gh api`, cached under library/ref-dates.json (successes only)."""

    def __init__(self, mem, repo, notes):
        self.mem, self.repo = mem, repo
        self.path = os.path.join(mem, 'library', 'ref-dates.json')
        self.cache = {}
        if os.path.isfile(self.path):
            self.cache = self.load(notes)
        self.failed = 0

    def load(self, notes):
        try:
            with open(self.path, encoding='utf-8') as fh:
                cache = json.load(fh)
        except (ValueError, OSError):
            cache = None
        if isinstance(cache, dict):
            return cache
        notes.append('ref-dates.json is unreadable: ignored, will be rebuilt')
        return {}

    def get(self, number):
        """Cached creation stamp, or None: lookups happen only in prefetch()."""
        return self.cache.get(self.repo, {}).get(str(number))

    def prefetch(self, numbers):
        """Fetch every uncached number in GraphQL batches; a number the response lacks counts as failed."""
        known = self.cache.setdefault(self.repo, {})
        todo = sorted({int(n) for n in numbers if str(int(n)) not in known})
        for i in range(0, len(todo), BATCH):
            batch = todo[i:i + BATCH]
            found = self.fetch(batch)
            for n in batch:
                if n in found:
                    known[str(n)] = found[n]
                else:
                    self.failed += 1

    def fetch(self, batch):
        """{number: created stamp} for the numbers one query answered; argv only, numbers are ints."""
        owner, name = self.repo.split('/', 1)
        fields = ' '.join(f'n{n}: issueOrPullRequest(number: {int(n)}) {{ ... on Issue {{ createdAt }} '
                          f'... on PullRequest {{ createdAt }} }}' for n in batch)
        query = f'query($owner: String!, $name: String!) {{ repository(owner: $owner, name: $name) {{ {fields} }} }}'
        try:
            done = subprocess.run(['gh', 'api', 'graphql', '-f', f'query={query}', '-f', f'owner={owner}',
                                   '-f', f'name={name}'], capture_output=True, text=True, timeout=120)
            repo = (json.loads(done.stdout).get('data') or {}).get('repository') or {}
        except (OSError, subprocess.TimeoutExpired, ValueError, AttributeError):
            return {}
        out = {}
        for n in batch:  # gh exits non-zero when one number is missing; the others in the response are still good
            stamp = (repo.get(f'n{n}') or {}).get('createdAt')
            if stamp and iso_day(stamp):
                out[n] = stamp
        return out

    def save(self):
        _lib.write_text(self.mem, self.path, json.dumps(self.cache, indent=1, sort_keys=True) + '\n')


def ref_source(mem, cfg, notes):
    """A RefDates, or None (with the reason in notes) when gh or github_repo is missing."""
    if not cfg.get('github_repo'):
        notes.append('issue/PR source skipped: no github_repo in classes.json')
    elif not REPO_RE.match(cfg['github_repo']):
        notes.append('issue/PR source skipped: github_repo is not owner/name')
    elif not shutil.which('gh'):
        notes.append('issue/PR source skipped: gh not found on PATH')
    else:
        return RefDates(mem, cfg['github_repo'], notes)
    return None


def cited(mem, fact, lines):
    text = ' '.join(lines)
    try:
        with open(os.path.join(mem, fact), encoding='utf-8') as fh:
            text += ' ' + fh.read()
    except (OSError, TypeError):
        pass
    return sorted({int(n) for n in _lib.REF_RE.findall(text)})


def bounded(refs, numbers, fm, tz):
    """not-before = newest cited issue/PR, with modified: (a not-after) making a range.

    A citation can be added in a later edit. When modified: predates the newest cited issue,
    the issue bounds only that later edit, not creation: the fact is known only to be no newer
    than modified:, so it is dated not-after modified: and the late citation is shown.
    """
    dated = [(iso_day(refs.get(n)), n) for n in numbers]
    dated = [(d, n) for d, n in dated if d]
    if not dated:
        return None
    newest, ref = max(dated)
    date = _lib.day_of(newest, tz)
    after = modified_day(fm.get('modified', ''), tz)
    if after and after >= date:
        return _lib.found(date, 'issue', 'range', not_after=after, ref=ref)
    if after:  # the citation came in a later edit: creation is bounded only by modified:
        return _lib.found(after, 'modified', 'not-after', ref=ref, cited_later=date)
    return _lib.found(date, 'issue', 'not-before', ref=ref)


def modified_day(value, tz):
    """Day of a modified: stamp in tz. An ISO timestamp is converted; a bare date is taken as written."""
    when = iso_day(value) if 'T' in value else None
    if when:
        return _lib.day_of(when, tz)
    if 'T' in value:
        return None  # an unparseable timestamp is not a date
    mod = _lib.DATE_RE.search(value)
    try:
        return datetime.date.fromisoformat('-'.join(mod.groups())).isoformat() if mod else None
    except ValueError:
        return None


def resolve(mem, cfg, refs=None, sessions=False):
    """{fact: info}. refs (a RefDates) and sessions=True enable the two non-local sources."""
    table, files, tz = {}, {}, _lib.zone(cfg)
    source = sorted((f, l) for f, l in _lib.source_lines(mem, cfg).items() if f)  # external entries have no fact
    if refs:
        refs.prefetch({n for f, l in source for n in cited(mem, f, l)})
    for fact, lines in source:
        fm = _lib.frontmatter(os.path.join(mem, fact))
        info = _lib.exact_date(fm, lines)
        sid = fm.get('originSessionId')
        if not info and sessions and sid:
            day = session_date(sid, tz)
            info = _lib.found(day, 'session', 'near-exact') if day else None
        if not info and refs:
            info = bounded(refs, cited(mem, fact, lines), fm, tz)
        if not info:
            day = _lib.file_date(mem, fact, tz)
            info = _lib.found(day, 'file', 'approximate') if day else _lib.found('unknown', 'none', 'unknown')
            files[fact] = day
        table[fact] = info
    return apply_bulk(table, files)


def apply_bulk(table, files):
    per_day = collections.Counter(d for d in files.values() if d)
    bulk = {d for d, n in per_day.items() if n >= _lib.BULK_THRESHOLD}
    for fact, day in files.items():
        if day in bulk:
            table[fact] = _lib.found('unknown', 'bulk', 'unknown')
    return table


def main(argv):
    if len(argv) != 2:
        _lib.die(__doc__)
    mem = os.path.abspath(argv[1])
    cfg = _lib.load_classes(mem)
    notes = []
    refs = ref_source(mem, cfg, notes)
    table = resolve(mem, cfg, refs, sessions=True)
    if refs:
        refs.save()
        if refs.failed:
            notes.append(f'{refs.failed} issue/PR lookups failed and were skipped')
    _lib.write_text(mem, os.path.join(mem, 'library', 'dates.json'),
                    json.dumps(table, indent=1, sort_keys=True, ensure_ascii=False) + '\n')
    for note in notes:
        print('dates: ' + note)
    counts = collections.Counter(i['quality'] for i in table.values())
    late = sum(1 for i in table.values() if i.get('cited_later'))
    print(f'dates: {len(table)} facts; ' + ', '.join(f'{q} {n}' for q, n in sorted(counts.items()))
          + f'; citations added after modified: (dated not-after modified:) {late}')


if __name__ == '__main__':
    main(sys.argv)
