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

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from test_memory_library import SCRIPTS, EXAMPLE, sha_tree  # noqa: E402

FILE_DAY = calendar.timegm((2026, 6, 9, 12, 0, 0))  # noon UTC: the same day in any zone the tests use
FAKE_GH = '''#!/bin/sh
echo "$2" >> "$GH_LOG"
case "$2" in
  */issues/101) echo 2026-09-14T08:00:00Z ;;
  */issues/202) echo 2026-09-20T08:00:00Z ;;
  *) exit 1 ;;
esac
'''
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


def run(script, mem, tmp, home, bin_dir):
    env = {'PATH': bin_dir + os.pathsep + '/nonexistent', 'MEMORY_LIBRARY_HOME': home,
           'GH_LOG': os.path.join(tmp, 'gh.log')}
    return subprocess.run([sys.executable, '-I', os.path.join(SCRIPTS, script), mem, *(['CI'] if script == 'build.py' else [])],
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

    def test_modified_earlier_than_cited_issue_is_shown_and_counted(self):
        c = self.d['f_clash.md']
        self.assertEqual((c['date'], c['quality'], c['conflict']), ('2026-09-20', 'not-before', '2026-09-01'))
        self.assertNotIn('not_after', c)
        self.assertIn('contradictions (modified earlier than a cited issue) 1', self.out.stdout)

    def test_never_edits_a_fact_file(self):
        self.assertEqual(sha_tree(self.mem, only_root=True), self.before)

    def test_cache_prevents_refetch_of_known_numbers(self):
        log = os.path.join(self.tmp, 'gh.log')
        first = open(log, encoding='utf-8').read().split()
        self.assertEqual(sorted(set(first)), sorted(first))  # each number fetched once per run
        run('dates.py', self.mem, self.tmp, self.home, self.bin)
        again = open(log, encoding='utf-8').read().split()
        self.assertEqual(len(again) - len(first), 1)  # only the failed #999 is retried
        cache = json.load(open(os.path.join(self.mem, 'library', 'ref-dates.json'), encoding='utf-8'))
        self.assertEqual(sorted(cache['owner/name']), ['101', '202'])

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
        self.assertIn('/≥2026-09-20` · ≥2026-09-20 (#202) ⚠ modified 2026-09-01 is earlier · ', line('2026-09.md', 'f_clash'))
        self.assertNotIn('f_before', text.get('2026-10.md', ''))  # a not-before is placed in its own month only
        self.assertEqual(sha_tree(self.mem, only_root=True), self.before)


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
