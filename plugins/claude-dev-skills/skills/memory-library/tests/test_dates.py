"""Tests for dates.py and the quality-marked dates in catalog.py (fake gh on PATH; the real gh is never called)."""
import calendar
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from test_memory_library import SCRIPTS, EXAMPLE, sha_tree  # noqa: E402

FILE_DAY = calendar.timegm((2026, 6, 9, 12, 0, 0))  # noon UTC: the same day in any zone the tests use
FAKE_GH = '''#!%s
import json, os, re, sys, time
args = sys.argv[1:]
time.sleep(float(os.environ.get('GH_SLEEP', '0')))
with open(os.environ['GH_LOG'], 'a') as log:
    if args[:2] != ['api', 'graphql']:
        log.write('other ' + ' '.join(args) + '\\n')
        sys.exit(1)
    query = next(a for a in args if a.startswith('query='))
    nums = [int(n) for n in re.findall(r'issueOrPullRequest\\(number: (\\d+)\\)', query)]
    log.write('graphql ' + ' '.join(map(str, nums)) + '\\n')
KNOWN = {101: '2026-09-14T08:00:00Z', 202: '2026-09-20T08:00:00Z'}
repo = {f'n{n}': ({'createdAt': KNOWN.get(n, '2026-07-01T08:00:00Z')} if n in KNOWN or n >= 5000 else None) for n in nums}
missing = [n for n in nums if repo[f'n{n}'] is None]
print(json.dumps({'data': {'repository': repo}, 'errors': [{'type': 'NOT_FOUND'}] if missing else None}))
sys.exit(1 if missing else 0)
''' % sys.executable
EXT_URL = 'https://example.com/o/r/issues/13483#issuecomment-'
EXT_DATED, EXT_UNDATED = 'Dated plan', 'Undated plan'
FACTS = {  # name -> (frontmatter extra lines, entry text)
    'f_created.md': ('  created: 2026-10-03\n', 'rule, see #101'),
    'f_text.md': ('', 'ledger rule 2026-11-12 see #101'),
    'f_trans.md': ('originSessionId: sess-trans\n', 'ledger note #101'),
    'f_hist.md': ('originSessionId: sess-hist\n', 'ledger note #101'),
    'f_before.md': ('', 'ledger rule, see #101 and #202 and #999'),
    'f_range.md': ('  modified: 2026-12-01\n', 'ledger rule, see #101'),
    'f_tz.md': ('originSessionId: sess-tz\n', 'ledger note'),
    'f_clash.md': ('  modified: 2026-09-01\n', 'ledger rule, see #202'),
    'f_file.md': ('', 'ledger rule without any date'),
}


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as fh:
        fh.write(text)


def make(drop_repo=False, tz='Europe/Riga'):
    tmp = tempfile.mkdtemp()
    home = os.path.join(tmp, 'home')
    mem = os.path.join(tmp, 'mem')
    lib = os.path.join(mem, 'library')
    os.makedirs(lib)
    cfg = json.load(open(EXAMPLE, encoding='utf-8'))
    if drop_repo:
        cfg.pop('github_repo')
    if tz:
        cfg['timezone'] = tz
    else:
        cfg.pop('timezone', None)
    write(os.path.join(lib, 'classes.json'), json.dumps(cfg))
    lines = []
    for name, (extra, text) in FACTS.items():
        meta = extra if extra.startswith('  ') else ''
        top = '' if extra.startswith('  ') else extra
        write(os.path.join(mem, name), f'---\nname: x\n{top}metadata:\n  type: feedback\n{meta}---\nbody\n')
        os.utime(os.path.join(mem, name), (FILE_DAY, FILE_DAY))
        lines.append(f'- [{name[:-3]}]({name}) - {text}')
    lines.append('- [Gone](f_missing.md) - ledger rule, no file')
    lines.append(f'- [{EXT_DATED}]({EXT_URL}) - ledger plan 2026-10-05')
    lines.append(f'- [{EXT_UNDATED}]({EXT_URL}2) - ledger plan, no date')
    write(os.path.join(mem, 'topics', 'ci-merge.md'), '# CI\n\n' + '\n'.join(lines) + '\n')
    write(os.path.join(home, '.claude', 'projects', 'p', 'sess-trans.jsonl'),
          '{"type":"x"}\n{"timestamp":"2026-08-02T23:30:00.000Z"}\n{"timestamp":"2026-08-01T10:00:00.000Z"}\n')
    write(os.path.join(home, '.claude', 'projects', 'p', 'sess-tz.jsonl'),
          '{"timestamp":"2026-08-05T23:30:00.000Z"}\n')
    write(os.path.join(home, '.claude', 'history.jsonl'),
          '{"timestamp":1788000000000,"sessionId":"sess-hist"}\n'
          '{"timestamp":1787000000000,"sessionId":"sess-hist"}\n'
          '{"timestamp":1700000000000,"sessionId":"other"}\n')
    return tmp, home, mem


def fake_gh(tmp, present=True):
    bin_dir = os.path.join(tmp, 'bin')
    os.makedirs(bin_dir)
    if present:
        gh = os.path.join(bin_dir, 'gh')
        write(gh, FAKE_GH)
        os.chmod(gh, os.stat(gh).st_mode | stat.S_IXUSR)
    return bin_dir


def run(script, mem, tmp, home, bin_dir, **extra_env):
    env = {'PATH': bin_dir + os.pathsep + '/nonexistent', 'MEMORY_LIBRARY_HOME': home,
           'GH_LOG': os.path.join(tmp, 'gh.log'), **extra_env}
    return subprocess.run([sys.executable, '-B', '-I', os.path.join(SCRIPTS, script), mem, *(['CI'] if script == 'build.py' else [])],
                          capture_output=True, text=True, env=env)


def dates(mem):
    return json.load(open(os.path.join(mem, 'library', 'dates.json'), encoding='utf-8'))


class WithGh(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp, cls.home, cls.mem = make()
        cls.bin = fake_gh(cls.tmp)
        cls.before = sha_tree(cls.mem, only_root=True)
        cls.out = run('dates.py', cls.mem, cls.tmp, cls.home, cls.bin)
        assert cls.out.returncode == 0, cls.out.stderr
        cls.d = dates(cls.mem)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp)

    def test_every_precedence_step(self):
        d = self.d
        self.assertEqual(d['f_created.md'], {'date': '2026-10-03', 'source': 'created', 'quality': 'exact'})
        self.assertEqual((d['f_text.md']['date'], d['f_text.md']['source'], d['f_text.md']['quality']),
                         ('2026-11-12', 'text', 'exact'))
        self.assertEqual((d['f_trans.md']['date'], d['f_trans.md']['source'], d['f_trans.md']['quality']),
                         ('2026-08-01', 'session', 'near-exact'))
        self.assertEqual((d['f_hist.md']['date'], d['f_hist.md']['quality']), ('2026-08-17', 'near-exact'))
        self.assertEqual((d['f_before.md']['date'], d['f_before.md']['quality'], d['f_before.md']['ref']),
                         ('2026-09-20', 'not-before', 202))
        self.assertEqual((d['f_range.md']['date'], d['f_range.md']['not_after'], d['f_range.md']['quality']),
                         ('2026-09-14', '2026-12-01', 'range'))
        self.assertEqual((d['f_file.md']['date'], d['f_file.md']['quality']), ('2026-06-09', 'approximate'))
        self.assertEqual(d['f_missing.md'], {'date': 'unknown', 'source': 'none', 'quality': 'unknown'})

    def test_session_day_is_in_the_configured_zone(self):
        self.assertEqual(self.d['f_tz.md']['date'], '2026-08-06')  # 23:30 UTC is 02:30 next day in Riga
        tmp, home, mem = make(tz='UTC')
        try:
            run('dates.py', mem, tmp, home, fake_gh(tmp))
            self.assertEqual(dates(mem)['f_tz.md']['date'], '2026-08-05')
        finally:
            shutil.rmtree(tmp)

    def test_no_timezone_key_uses_the_machine_local_zone(self):
        tmp, home, mem = make(tz=None)
        try:
            run('dates.py', mem, tmp, home, fake_gh(tmp), TZ='Asia/Tokyo')
            self.assertEqual(dates(mem)['f_tz.md']['date'], '2026-08-06')  # 23:30 UTC is 08:30 next day in Tokyo
            run('dates.py', mem, tmp, home, os.path.join(tmp, 'bin'), TZ='America/Los_Angeles')
            self.assertEqual(dates(mem)['f_tz.md']['date'], '2026-08-05')  # 16:30 the same day in Los Angeles
        finally:
            shutil.rmtree(tmp)

    def test_corrupt_ref_cache_is_ignored_and_rebuilt(self):
        tmp, home, mem = make()
        try:
            write(os.path.join(mem, 'library', 'ref-dates.json'), '{"owner/name": {"101": ')
            out = run('dates.py', mem, tmp, home, fake_gh(tmp))
            self.assertEqual(out.returncode, 0, out.stderr)
            self.assertEqual(sum('ref-dates.json is unreadable' in ln for ln in out.stdout.splitlines()), 1)
            self.assertEqual(dates(mem)['f_before.md']['date'], '2026-09-20')
            with open(os.path.join(mem, 'library', 'ref-dates.json'), encoding='utf-8') as fh:
                self.assertEqual(sorted(json.load(fh)['owner/name']), ['101', '202'])
        finally:
            shutil.rmtree(tmp)

    def test_fact_missing_from_dates_json_gets_its_local_date(self):
        tmp, home, mem = make()
        try:
            gh = fake_gh(tmp)
            run('dates.py', mem, tmp, home, gh)
            run('build.py', mem, tmp, home, gh)
            write(os.path.join(mem, 'newer.md'), '---\nname: n\nmetadata:\n  type: feedback\n  created: 2026-11-20\n---\n')
            with open(os.path.join(mem, 'topics', 'ci-merge.md'), 'a', encoding='utf-8') as fh:
                fh.write('- [Newer](newer.md) - ledger rule\n')
            run('build.py', mem, tmp, home, gh)
            c = run('catalog.py', mem, tmp, home, gh)
            self.assertIn('1 facts missing from dates.json', c.stdout)
            with open(os.path.join(mem, 'library', 'catalog', 'by-date', '2026-11.md'), encoding='utf-8') as fh:
                self.assertIn('/2026-11-20` · ', next(x for x in fh if 'newer.md' in x))
        finally:
            shutil.rmtree(tmp)

    def test_citation_added_after_modified_dates_the_fact_not_after_modified(self):
        c = self.d['f_clash.md']
        self.assertEqual((c['date'], c['quality'], c['cited_later'], c['ref']), ('2026-09-01', 'not-after', '2026-09-20', 202))
        self.assertIn('citations added after modified: (dated not-after modified:) 1', self.out.stdout)

    def test_modified_iso_stamp_is_read_in_the_configured_zone(self):
        sys.path.insert(0, SCRIPTS)
        import dates
        riga = __import__('zoneinfo').ZoneInfo('Europe/Riga')
        self.assertEqual(dates.modified_day('2026-08-17T22:28:25.515Z', riga), '2026-08-18')
        self.assertEqual(dates.modified_day('2026-08-17T20:00:00Z', riga), '2026-08-17')
        self.assertEqual(dates.modified_day('2026-08-17', riga), '2026-08-17')
        self.assertEqual(dates.modified_day('2026-08-17T22:28:25.5Z', riga), '2026-08-18')
        self.assertIsNone(dates.modified_day('2026-13-45T99:00Z', riga))
        self.assertIsNone(dates.modified_day('2026-13-45', riga))

    def test_never_edits_a_fact_file(self):
        self.assertEqual(sha_tree(self.mem, only_root=True), self.before)

    def test_cache_prevents_refetch_of_known_numbers(self):
        log = os.path.join(self.tmp, 'gh.log')
        first = open(log, encoding='utf-8').read().splitlines()
        asked = [n for ln in first for n in ln.split()[1:]]
        self.assertEqual(len(first), 1)  # one batched call for every cited number
        self.assertEqual(sorted(set(asked)), sorted(asked))  # each number fetched once per run
        self.assertEqual(sorted(asked), ['101', '202', '999'])
        run('dates.py', self.mem, self.tmp, self.home, self.bin)
        again = open(log, encoding='utf-8').read().splitlines()
        self.assertEqual(again[len(first):], ['graphql 999'])  # only the missing #999 is retried
        cache = json.load(open(os.path.join(self.mem, 'library', 'ref-dates.json'), encoding='utf-8'))
        self.assertEqual(sorted(cache['owner/name']), ['101', '202'])

    def test_missing_number_in_a_batch_is_a_failure_not_cached(self):
        self.assertIn('1 issue/PR lookups failed and were skipped', self.out.stdout)
        cache = json.load(open(os.path.join(self.mem, 'library', 'ref-dates.json'), encoding='utf-8'))
        self.assertNotIn('999', cache['owner/name'])
        self.assertEqual(self.d['f_before.md']['ref'], 202)  # the answered numbers in the same batch still date it

    def test_external_entries_are_shelved_not_missing_and_not_facts(self):
        b = run('build.py', self.mem, self.tmp, self.home, self.bin)
        self.assertIn("1 missing targets ['f_missing.md']", b.stdout)
        self.assertEqual([k for k in self.d if 'http' in k or 'issuecomment' in k], [])
        chapter = ''.join(open(os.path.join(base, f), encoding='utf-8').read()
                          for base, _, fs in os.walk(os.path.join(self.mem, 'library', 'reference')) for f in fs)
        self.assertIn(f']({EXT_URL})', chapter)  # the URL is kept as written, not rewritten to a file path
        self.assertEqual(run('catalog.py', self.mem, self.tmp, self.home, self.bin).returncode, 0)
        by = os.path.join(self.mem, 'library', 'catalog', 'by-date')
        dated = open(os.path.join(by, '2026-10.md'), encoding='utf-8').read()
        undated = open(os.path.join(by, 'unknown.md'), encoding='utf-8').read()
        self.assertIn(EXT_DATED, dated)  # dated from text in its line only
        self.assertIn(EXT_UNDATED, undated)
        self.assertNotIn(EXT_DATED, undated)

    def test_unchanged_dates_json_keeps_its_mtime(self):
        path = os.path.join(self.mem, 'library', 'dates.json')
        m = os.stat(path).st_mtime_ns
        run('dates.py', self.mem, self.tmp, self.home, self.bin)
        self.assertEqual(os.stat(path).st_mtime_ns, m)

    def test_catalog_shows_quality_never_upgraded(self):
        self.assertEqual(run('build.py', self.mem, self.tmp, self.home, self.bin).returncode, 0)
        c = run('catalog.py', self.mem, self.tmp, self.home, self.bin)
        self.assertEqual(c.returncode, 0, c.stderr)
        by = os.path.join(self.mem, 'library', 'catalog', 'by-date')
        text = {f: open(os.path.join(by, f), encoding='utf-8').read() for f in os.listdir(by)}
        line = lambda f, key: next(x for x in text[f].splitlines() if key in x)  # noqa: E731
        self.assertIn('/2026-10-03` · ', line('2026-10.md', 'f_created'))
        self.assertIn('/≈2026-08-01` · ', line('2026-08.md', 'f_trans'))
        self.assertIn('/≥2026-09-20` · ≥2026-09-20 (#202) · ', line('2026-09.md', 'f_before'))
        self.assertIn('/≥2026-09-14` · ≥2026-09-14 ≤2026-12-01 (#101) · ', line('2026-09.md', 'f_range'))
        self.assertIn('/~2026-06-09` · ', line('2026-06.md', 'f_file'))
        self.assertIn('/unknown` · ', line('unknown.md', 'f_missing'))
        self.assertIn('/≤2026-09-01` · ≤2026-09-01 (cites #202 from 2026-09-20: added in a later edit) · ', line('2026-09.md', 'f_clash'))
        self.assertNotIn('f_before', text.get('2026-10.md', ''))  # a not-before is placed in its own month only
        self.assertEqual(sha_tree(self.mem, only_root=True), self.before)


class Batching(unittest.TestCase):
    def test_numbers_are_batched_fifty_per_query(self):
        tmp, home, mem = make()
        try:
            extra = ''.join(f'- [B{i}](b{i}.md) - ledger rule #{5000 + i}\n' for i in range(120))
            for i in range(120):
                write(os.path.join(mem, f'b{i}.md'), '---\nname: b\nmetadata:\n  type: feedback\n---\n')
            with open(os.path.join(mem, 'topics', 'ci-merge.md'), 'a', encoding='utf-8') as fh:
                fh.write(extra)
            out = run('dates.py', mem, tmp, home, fake_gh(tmp))
            self.assertEqual(out.returncode, 0, out.stderr)
            calls = open(os.path.join(tmp, 'gh.log'), encoding='utf-8').read().splitlines()
            self.assertEqual([len(c.split()) - 1 for c in calls], [50, 50, 23])  # 120 new + 101, 202, 999
            self.assertEqual(dates(mem)['b7.md']['date'], '2026-07-01')
        finally:
            shutil.rmtree(tmp)

    def test_only_digits_reach_the_query(self):
        sys.path.insert(0, SCRIPTS)
        import dates as d
        seen = []
        fake = lambda argv, **kw: (seen.append(argv), type('R', (), {'stdout': '{}', 'returncode': 1})())[1]  # noqa: E731
        with mock.patch.object(d.subprocess, 'run', fake):
            d.RefDates('/nonexistent', 'o/r', []).fetch([7, 8])
        self.assertEqual(seen[0][:3], ['gh', 'api', 'graphql'])
        self.assertEqual([a for a in seen[0] if a.startswith('query=')][0].count('number: '), 2)


class Hardening(unittest.TestCase):
    def fetch(self, stdout):
        sys.path.insert(0, SCRIPTS)
        import dates as d
        fake = lambda argv, **kw: type('R', (), {'stdout': stdout, 'returncode': 1})()  # noqa: E731
        with mock.patch.object(d.subprocess, 'run', fake):
            return d.RefDates('/nonexistent', 'o/r', []).fetch([7, 8, 9, 10])

    def test_non_dict_nodes_are_missing_numbers(self):
        body = '{"data":{"repository":{"n7":"x","n8":["y"],"n9":5,"n10":{"createdAt":"2026-07-01T08:00:00Z"}}}}'
        self.assertEqual(self.fetch(body), {10: '2026-07-01T08:00:00Z'})
        self.assertEqual(self.fetch('{"data":{"repository":"x"}}'), {})

    def test_corrupt_repo_entry_is_rebuilt_with_one_note(self):
        tmp, home, mem = make()
        try:
            write(os.path.join(mem, 'library', 'ref-dates.json'), '{"owner/name": ["x"]}')
            out = run('dates.py', mem, tmp, home, fake_gh(tmp))
            self.assertEqual(out.returncode, 0, out.stderr)
            self.assertEqual(sum('entry for owner/name is unreadable' in ln for ln in out.stdout.splitlines()), 1)
            with open(os.path.join(mem, 'library', 'ref-dates.json'), encoding='utf-8') as fh:
                self.assertEqual(sorted(json.load(fh)['owner/name']), ['101', '202'])
        finally:
            shutil.rmtree(tmp)


class WithoutGh(unittest.TestCase):
    def check(self, drop_repo, present, message):
        tmp, home, mem = make(drop_repo)
        try:
            before = sha_tree(mem, only_root=True)
            out = run('dates.py', mem, tmp, home, fake_gh(tmp, present))
            self.assertEqual(out.returncode, 0, out.stderr)
            self.assertEqual(sum(message in ln for ln in out.stdout.splitlines()), 1, out.stdout)
            d = dates(mem)
            self.assertEqual(d['f_before.md']['quality'], 'approximate')  # no guess from a skipped source
            self.assertEqual(d['f_trans.md']['quality'], 'near-exact')  # local sources still work
            self.assertFalse(os.path.exists(os.path.join(mem, 'library', 'ref-dates.json')))
            self.assertEqual(sha_tree(mem, only_root=True), before)
        finally:
            shutil.rmtree(tmp)

    def test_no_gh(self):
        self.check(False, False, 'gh not found')

    def test_no_github_repo(self):
        self.check(True, True, 'no github_repo')

    def test_catalog_without_dates_json_uses_local_sources_only(self):
        tmp, home, mem = make()
        try:
            run('build.py', mem, tmp, home, fake_gh(tmp))
            self.assertEqual(run('catalog.py', mem, tmp, home, os.path.join(tmp, 'bin')).returncode, 0)
            with open(os.path.join(mem, 'library', 'catalog', 'by-date', '2026-06.md'), encoding='utf-8') as fh:
                self.assertEqual(fh.read().count('/~2026-06-09`'), 7)  # file time, nothing upgraded
        finally:
            shutil.rmtree(tmp)


if __name__ == '__main__':
    unittest.main()
