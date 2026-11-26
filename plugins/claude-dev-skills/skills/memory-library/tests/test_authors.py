"""Tests for authors.py and its use by build.py and catalog.py (fake ledger on PATH; the real ledger is never called)."""
import json
import os
import shutil
import stat
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from test_dates import make, fake_gh, run, write  # noqa: E402
from test_memory_library import sha_tree  # noqa: E402

LEDGER = f'''#!{sys.executable}
print("autobot-ai-m2      no beat    sid abcd1234  socket 1.sock    seen 11-19 00:41")
print("autobot-ai-old     no beat    sid 11112222  socket 2.sock    seen 11-19 00:41")
print("autobot-ai-bad     no beat    socket 99998888.sock seen 11-19 00:41  (was sidecar 77776666)")
print("autobot-ai-twin    no beat    sid 33334444  socket 3.sock    seen 11-19 00:41")
print("autobot-ai-twin2   no beat    sid 33334444  socket 4.sock    seen 11-19 00:41")
'''
SESSIONS = {  # fact -> (frontmatter lines, expected author, expected source)
    'a_front.md': ('author: carol\noriginSessionId: abcd1234-0000-0000-0000-000000000000\n', 'carol', 'frontmatter'),
    'a_ledger.md': ('originSessionId: abcd1234-0000-0000-0000-000000000000\n', 'autobot-ai-m2', 'ledger'),
    'a_unknown.md': ('originSessionId: ffff0000-0000-0000-0000-000000000000\n', 'unrecorded', 'unresolved'),
    'a_twin.md': ('originSessionId: 33334444-0000-0000-0000-000000000000\n', 'unrecorded', 'unresolved'),
    'a_other_column.md': ('originSessionId: 99998888-0000-0000-0000-000000000000\n', 'unrecorded', 'unresolved'),
    'a_none.md': ('', 'unrecorded', 'unresolved'),
}


def with_facts(ledger=True, cfg_edit=None):
    tmp, home, mem = make()
    bin_dir = fake_gh(tmp)
    if ledger:
        path = os.path.join(bin_dir, 'ledger')
        write(path, LEDGER)
        os.chmod(path, os.stat(path).st_mode | stat.S_IXUSR)
    lines = []
    for name, (fm, _, _) in SESSIONS.items():
        write(os.path.join(mem, name), f'---\nname: x\n{fm}metadata:\n  type: feedback\n---\nbody\n')
        lines.append(f'- [{name[:-3]}]({name}) - ledger note')
    with open(os.path.join(mem, 'topics', 'ci-merge.md'), 'a', encoding='utf-8') as fh:
        fh.write('\n'.join(lines) + '\n')
    if cfg_edit:
        path = os.path.join(mem, 'library', 'classes.json')
        with open(path, encoding='utf-8') as fh:
            cfg = json.load(fh)
        cfg_edit(cfg)
        write(path, json.dumps(cfg))
    return tmp, home, mem, bin_dir


def authors(mem):
    with open(os.path.join(mem, 'library', 'authors.json'), encoding='utf-8') as fh:
        return json.load(fh)


class WithLedger(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp, cls.home, cls.mem, cls.bin = with_facts()
        cls.before = sha_tree(cls.mem, only_root=True)
        cls.out = run('authors.py', cls.mem, cls.tmp, cls.home, cls.bin)
        assert cls.out.returncode == 0, cls.out.stderr

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp)

    def test_resolved_and_unresolved(self):
        table = authors(self.mem)
        for name, (_, author, source) in SESSIONS.items():
            self.assertEqual(table[name], {'author': author, 'source': source}, name)

    def test_never_edits_a_fact_file(self):
        self.assertEqual(sha_tree(self.mem, only_root=True), self.before)
        self.assertNotIn('not found', self.out.stdout)  # nothing to warn about when the ledger answered

    def test_build_places_resolved_facts_in_their_authors_book_and_catalog_counts(self):
        self.assertEqual(run('build.py', self.mem, self.tmp, self.home, self.bin).returncode, 0)
        ci = os.path.join(self.mem, 'library', 'reference', 'ci-merge')
        self.assertTrue(any('a_ledger' in open(os.path.join(ci, 'autobot-ai-m2', f), encoding='utf-8').read()
                            for f in os.listdir(os.path.join(ci, 'autobot-ai-m2'))))
        self.assertTrue(os.path.isdir(os.path.join(ci, 'carol')))  # frontmatter author, as before
        self.assertEqual(run('dates.py', self.mem, self.tmp, self.home, self.bin).returncode, 0)
        self.assertEqual(run('catalog.py', self.mem, self.tmp, self.home, self.bin).returncode, 0)
        with open(os.path.join(self.mem, 'library', 'catalog', 'by-author.md'), encoding='utf-8') as fh:
            text = fh.read()
        self.assertIn('Authors resolved: 2 (2 entries); unrecorded: ', text)
        self.assertEqual(sha_tree(self.mem, only_root=True), self.before)

    def test_one_pass_authors_then_build_places_the_fact(self):
        tmp, home, mem, bin_dir = with_facts()
        try:
            self.assertEqual(run('authors.py', mem, tmp, home, bin_dir).returncode, 0)
            self.assertEqual(run('build.py', mem, tmp, home, bin_dir).returncode, 0)
            book = os.path.join(mem, 'library', 'reference', 'ci-merge', 'autobot-ai-m2')
            self.assertTrue(any('a_ledger' in open(os.path.join(book, f), encoding='utf-8').read()
                                for f in os.listdir(book)))
        finally:
            shutil.rmtree(tmp)

    def test_unchanged_authors_json_keeps_its_mtime(self):
        path = os.path.join(self.mem, 'library', 'authors.json')
        m = os.stat(path).st_mtime_ns
        run('authors.py', self.mem, self.tmp, self.home, self.bin)
        self.assertEqual(os.stat(path).st_mtime_ns, m)


class WithoutLedger(unittest.TestCase):
    def check(self, message, ledger=False, cfg_edit=None):
        tmp, home, mem, bin_dir = with_facts(ledger, cfg_edit)
        try:
            before = sha_tree(mem, only_root=True)
            out = run('authors.py', mem, tmp, home, bin_dir)
            self.assertEqual(out.returncode, 0, out.stderr)
            self.assertEqual(sum(message in ln for ln in out.stdout.splitlines()), 1, out.stdout)
            table = authors(mem)
            self.assertEqual(table['a_front.md'], {'author': 'carol', 'source': 'frontmatter'})
            for name in ('a_ledger.md', 'a_unknown.md', 'a_twin.md', 'a_none.md', 'a_other_column.md'):
                self.assertEqual(table[name], {'author': 'unrecorded', 'source': 'unresolved'}, name)
            self.assertEqual(sha_tree(mem, only_root=True), before)
        finally:
            shutil.rmtree(tmp)

    def test_ledger_command_not_found(self):
        self.check('not found')

    def test_no_ledger_cmd_configured(self):
        self.check('no ledger configured', cfg_edit=lambda cfg: cfg.pop('ledger_cmd'))

    def test_unsafe_or_empty_ledger_cmd_is_refused(self):
        for bad in ('', '  ', 'ledger; rm -rf x', 'ledger | cat', '$(x)'):
            tmp, home, mem, bin_dir = with_facts(True, lambda cfg: cfg.update(ledger_cmd=bad))
            try:
                out = run('authors.py', mem, tmp, home, bin_dir)
                self.assertEqual(out.returncode, 2, bad)
                self.assertIn('plain command or path', out.stderr)
            finally:
                shutil.rmtree(tmp)

    def test_catalog_without_authors_json_says_so(self):
        tmp, home, mem, bin_dir = with_facts(False)
        try:
            run('build.py', mem, tmp, home, bin_dir)
            self.assertEqual(run('catalog.py', mem, tmp, home, bin_dir).returncode, 0)
            with open(os.path.join(mem, 'library', 'catalog', 'by-author.md'), encoding='utf-8') as fh:
                self.assertIn('authors.json is absent (run authors.py)', fh.read())
        finally:
            shutil.rmtree(tmp)


if __name__ == '__main__':
    unittest.main()
