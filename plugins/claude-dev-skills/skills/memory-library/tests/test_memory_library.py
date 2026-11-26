"""Tests for memory-library: build, catalog, call numbers and the new-fact hook.

Run: python3 -m unittest discover -s plugins/claude-dev-skills/skills/memory-library/tests -v
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest

SKILL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(SKILL, 'scripts')
EXAMPLE = os.path.join(SKILL, 'references', 'classes.example.json')
sys.path.insert(0, SCRIPTS)
import _lib  # noqa: E402

BULK_DAY = time.mktime((2026, 5, 4, 12, 0, 0, 0, 0, -1))
OTHER_DAY = time.mktime((2026, 6, 9, 12, 0, 0, 0, 0, -1))


def run(script, *args, stdin=None):
    return subprocess.run([sys.executable, '-I', os.path.join(SCRIPTS, script), *args],
                          input=stdin, capture_output=True, text=True)


def sha_tree(root, only_root=False):
    out = {}
    for base, dirs, files in os.walk(root):
        if only_root and base != root:
            continue
        for f in files:
            p = os.path.join(base, f)
            with open(p, 'rb') as fh:
                out[os.path.relpath(p, root)] = hashlib.sha256(fh.read()).hexdigest()
    return out


NEW_FACT = 'feedback_new_lock.md'
NEW_LINE = '- [New lock rule](feedback_new_lock.md) - ledger lock rule, see #4321'


def make_fixture(n_bulk=22, new_fact=False):
    tmp = tempfile.mkdtemp()
    mem = os.path.join(tmp, '.claude', 'projects', 'demo', 'memory')
    os.makedirs(os.path.join(mem, 'topics'))
    os.makedirs(os.path.join(mem, 'library'))
    shutil.copy(EXAMPLE, os.path.join(mem, 'library', 'classes.json'))
    lines = []

    def fact(name, body='body', mtime=None):
        with open(os.path.join(mem, name), 'w', encoding='utf-8') as fh:
            fh.write(body)
        if mtime:
            os.utime(os.path.join(mem, name), (mtime, mtime))

    for i in range(n_bulk):  # copied on one day, session notes about trains
        fact(f'gotcha_train_{i}.md', '---\nname: t\nmetadata:\n  type: gotcha\n---\n', BULK_DAY)
        lines.append(f'- [Train note {i}](../gotcha_train_{i}.md) - a train rule, see #12{i:02d}')
    fact('feedback_review_rule.md', '---\nname: r\nmetadata:\n  type: feedback\n---\n', OTHER_DAY)
    lines.append('- [Review rule](feedback_review_rule.md) - reviewer approval is needed')
    fact('feedback_dated.md', 'x', OTHER_DAY)
    lines.append('- [Dated lock](feedback_dated.md) - ledger lock rule 2026-11-12')
    fact('note_written.md', '---\nname: n\nmetadata:\n  author: sess-a\n  created: 2026-10-03\n---\n', OTHER_DAY)
    lines.append('- [Written ledger note](note_written.md) - ledger entry')
    fact('feedback_old.md', 'x', OTHER_DAY)
    lines.append('- [Old rule](feedback_old.md) - SUPERSEDED train rule 2026-09-01')
    if new_fact:
        fact(NEW_FACT, '---\nname: l\nmetadata:\n  type: feedback\n  created: 2026-11-20\n---\n', OTHER_DAY)
        lines.append(NEW_LINE)
    write_source(mem, lines)
    return tmp, mem


def write_source(mem, lines):
    with open(os.path.join(mem, 'topics', 'ci-merge.md'), 'w', encoding='utf-8') as fh:
        fh.write('# CI\n\n' + '\n'.join(lines) + '\n')


class BuildCatalogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp, cls.mem = make_fixture()
        cls.before = sha_tree(cls.mem)
        cls.root_before = {k: v for k, v in cls.before.items() if os.sep not in k}
        b = run('build.py', cls.mem, 'CI')
        c = run('catalog.py', cls.mem)
        assert b.returncode == 0, b.stderr
        assert c.returncode == 0, c.stderr

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp)

    def read(self, *parts):
        with open(os.path.join(self.mem, 'library', *parts), encoding='utf-8') as fh:
            return fh.read()

    def test_fact_files_byte_identical(self):
        after = sha_tree(self.mem, only_root=True)
        self.assertEqual(after, self.root_before)
        self.assertEqual(len(after), 26)
        topics = {k: v for k, v in sha_tree(self.mem).items() if k.startswith('topics')}
        self.assertEqual(topics, {k: v for k, v in self.before.items() if k.startswith('topics')})

    def test_idempotent(self):
        first = sha_tree(os.path.join(self.mem, 'library'))
        run('build.py', self.mem, 'CI')
        run('catalog.py', self.mem)
        self.assertEqual(sha_tree(os.path.join(self.mem, 'library')), first)

    def test_rooms_and_authors(self):
        self.assertTrue(os.path.isfile(self.read_path('reference', 'ci-merge', 'owner', 'review-approval.md')))
        self.assertTrue(os.path.isfile(self.read_path('archive', 'ci-merge', 'owner', 'superseded.md')))
        self.assertTrue(os.path.isfile(self.read_path('reference', 'ci-merge', 'sess-a', 'locks-ledger.md')))
        self.assertIn('trains-queue', self.read('reference', 'ci-merge', 'CARD.md'))

    def read_path(self, *parts):
        return os.path.join(self.mem, 'library', *parts)

    def test_bulk_dates_become_unknown(self):
        unknown = self.read('catalog', 'by-date', 'unknown.md')
        self.assertEqual(unknown.count('Train note'), 22)
        self.assertIn('REF.CI/sessions/TRN/unknown', unknown)

    def test_below_threshold_stays_approximate(self):
        tmp, mem = make_fixture(n_bulk=19)
        try:
            run('build.py', mem, 'CI')
            run('catalog.py', mem)
            with open(os.path.join(mem, 'library', 'catalog', 'by-date', '2026-05.md'), encoding='utf-8') as fh:
                text = fh.read()
            self.assertEqual(text.count('REF.CI/sessions/TRN/~2026-05-04'), 19)
            self.assertFalse(os.path.exists(os.path.join(mem, 'library', 'catalog', 'by-date', 'unknown.md')))
        finally:
            shutil.rmtree(tmp)

    def test_created_and_text_dates_are_exact(self):
        self.assertIn('REF.CI/sess-a/LCK/2026-10-03', self.read('catalog', 'by-date', '2026-10.md'))
        self.assertIn('REF.CI/owner/LCK/2026-11-12', self.read('catalog', 'by-date', '2026-11.md'))
        self.assertIn('ARC.CI/owner/SUP/2026-09-01', self.read('catalog', 'by-date', '2026-09.md'))

    def test_every_catalogue_exists_and_lines_carry_call_numbers(self):
        for name in ('by-topic', 'by-author', 'by-date', 'by-title', 'by-kind', 'by-issue'):
            self.assertTrue(os.path.isfile(self.read_path('catalog', name + '.md')), name)
        cat = self.read_path('catalog')
        for sub in ('by-date', 'by-title', 'by-kind', 'by-issue'):
            for f in os.listdir(os.path.join(cat, sub)):
                with open(os.path.join(cat, sub, f), encoding='utf-8') as fh:
                    entries = [ln for ln in fh if ln.startswith('- ')]
                self.assertTrue(entries)
                for ln in entries:
                    self.assertRegex(ln, r'^- `[A-Z]+\.[A-Z]+/[^/`]+/[A-Z]+/([~≈≥]?\d{4}-\d{2}-\d{2}|unknown)` · ')

    def test_kind_and_issue_groups(self):
        self.assertTrue(os.path.isfile(self.read_path('catalog', 'by-kind', 'gotcha.md')))
        self.assertTrue(os.path.isfile(self.read_path('catalog', 'by-kind', 'feedback.md')))
        self.assertIn('Train note 0', self.read('catalog', 'by-issue', '1xxx.md'))

    def test_links_resolve_to_fact_files(self):
        text = self.read('catalog', 'by-title', 'T.md')
        self.assertIn('](../../../gotcha_train_0.md)', text)


def mtimes(root):
    return {os.path.relpath(os.path.join(b, f), root): os.stat(os.path.join(b, f)).st_mtime_ns
            for b, _, fs in os.walk(root) for f in fs}


class FullBuildWriteSetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.full_tmp, cls.full = make_fixture(new_fact=True)
        for cmd in (('build.py', cls.full, 'CI'), ('catalog.py', cls.full)):
            assert run(*cmd).returncode == 0
        cls.tmp, cls.mem = make_fixture()
        for cmd in (('build.py', cls.mem, 'CI'), ('catalog.py', cls.mem)):
            assert run(*cmd).returncode == 0
        cls.lib = os.path.join(cls.mem, 'library')
        old = time.time() - 86400
        for b, _, fs in os.walk(cls.lib):
            for f in fs:
                os.utime(os.path.join(b, f), (old, old))
        cls.mt_before = mtimes(cls.lib)
        cls.sha_before = sha_tree(cls.lib)
        shutil.copy(os.path.join(cls.full, NEW_FACT), os.path.join(cls.mem, NEW_FACT))
        with open(os.path.join(cls.mem, 'topics', 'ci-merge.md'), encoding='utf-8') as fh:
            lines = [ln.rstrip('\n') for ln in fh if ln.startswith('- [')]
        write_source(cls.mem, lines + [NEW_LINE])
        cls.res = [run('build.py', cls.mem, 'CI'), run('catalog.py', cls.mem)]

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)
        shutil.rmtree(cls.full_tmp, ignore_errors=True)

    def test_succeeds(self):
        for r in self.res:
            self.assertEqual(r.returncode, 0, r.stderr)

    def test_byte_identical_to_build_with_the_fact_from_the_start(self):
        lib = sha_tree(self.lib)
        self.assertEqual(lib, sha_tree(os.path.join(self.full, 'library')))

    def test_only_the_touched_files_change(self):
        after = mtimes(self.lib)
        changed = {k for k in after if after[k] != self.mt_before.get(k)}
        cat = 'catalog' + os.sep
        expected = set()
        for k in after:
            with open(os.path.join(self.lib, k), encoding='utf-8') as fh:
                lists_fact = NEW_FACT in fh.read()
            if k.startswith(cat) and os.sep not in k[len(cat):]:
                expected.add(k)  # catalogue indexes carry the counts
            elif k.endswith('CARD.md') or lists_fact:
                expected.add(k)  # the shelf card, the chapter and the groups listing the fact
        self.assertEqual(changed, expected)
        self.assertEqual(sum(1 for k in changed if not k.startswith(cat) and not k.endswith('CARD.md')), 1)
        untouched = [k for k in after if k not in changed]
        self.assertTrue(untouched)
        sha_now = sha_tree(self.lib)
        for k in untouched:
            self.assertEqual(sha_now[k], self.sha_before[k], k)

    def test_existing_facts_untouched(self):
        self.assertEqual(sha_tree(self.mem, only_root=True),
                         sha_tree(os.path.join(self.full, ''), only_root=True))


class WriteGuardTests(unittest.TestCase):
    def setUp(self):
        self.tmp, self.mem = make_fixture(n_bulk=1)
        self.outside = os.path.join(self.tmp, 'outside')
        os.makedirs(self.outside)

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_write_text_refuses_dotdot_dir(self):
        with self.assertRaises(RuntimeError):
            _lib.write_text(self.mem, os.path.join(self.mem, 'library', '..', '..', 'x.md'), 'x')
        self.assertFalse(os.path.exists(os.path.join(os.path.dirname(self.mem), 'x.md')))

    def test_classes_with_dotdot_room_dir_writes_nothing_outside(self):
        path = os.path.join(self.mem, 'library', 'classes.json')
        with open(path, encoding='utf-8') as fh:
            cfg = json.load(fh)
        cfg['rooms']['REF']['dir'] = '../..'
        with open(path, 'w', encoding='utf-8') as fh:
            json.dump(cfg, fh)
        before = sha_tree(self.tmp)
        r = run('build.py', self.mem, 'CI')
        self.assertNotEqual(r.returncode, 0)
        self.assertIn('refusing to write outside library/', r.stderr)
        self.assertEqual(sha_tree(self.tmp), before)

    def test_symlinked_dir_pointing_outside_is_refused(self):
        os.symlink(self.outside, os.path.join(self.mem, 'library', 'reference'))
        with self.assertRaises(RuntimeError):
            _lib.write_text(self.mem, os.path.join(self.mem, 'library', 'reference', 'a.md'), 'x')
        r = run('build.py', self.mem, 'CI')
        self.assertNotEqual(r.returncode, 0)
        self.assertEqual(os.listdir(self.outside), [])


class CallNumberTests(unittest.TestCase):
    def test_format_follows_facet_order(self):
        self.assertEqual(_lib.call_number('REF', 'CI', 'owner', 'TRN', '2026-11-12'),
                         'REF.CI/owner/TRN/2026-11-12')
        self.assertEqual(_lib.call_number('REF', 'CI', 'owner', 'TRN', '2026-11-12', approx=True),
                         'REF.CI/owner/TRN/~2026-11-12')
        self.assertEqual(_lib.call_number('REF', 'CI', 'owner', 'TRN', 'unknown', approx=True),
                         'REF.CI/owner/TRN/unknown')

    def test_sort_order_is_room_shelf_author_chapter_date(self):
        rows = [('REF', 'CI', 'owner', 'TRN', '2026-11-12'), ('ARC', 'CI', 'sessions', 'TRN', '2026-01-01'),
                ('REF', 'CI', 'owner', 'TRN', '2026-01-01'), ('REF', 'CI', 'owner', 'LCK', '2026-12-01'),
                ('REF', 'CI', 'agent', 'TRN', '2026-12-01'), ('REF', 'GIT', 'agent', 'AAA', '2020-01-01')]
        got = sorted(rows, key=lambda r: _lib.sort_key(*r))
        self.assertEqual(got, [rows[1], rows[4], rows[3], rows[2], rows[0], rows[5]])
        calls = [_lib.call_number(*r) for r in got]
        self.assertEqual(calls, sorted(calls))


HOOK = os.path.join(SCRIPTS, 'check_new_fact.py')


def hook(tool, path, content='', name='Write'):
    payload = {'hook_event_name': 'PreToolUse', 'tool_name': name,
               'tool_input': {'file_path': path, 'content': content}}
    return subprocess.run([sys.executable, '-I', HOOK], input=json.dumps(payload),
                          capture_output=True, text=True)


GOOD = '---\nname: a\nmetadata:\n  type: feedback\n  author: owner\n  created: 2026-11-12\n---\nbody\n'


class HookTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.mem = os.path.join(self.tmp, '.claude', 'projects', 'any-project', 'memory')
        os.makedirs(os.path.join(self.mem, 'topics'))
        os.makedirs(os.path.join(self.mem, 'library'))

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def p(self, *parts):
        return os.path.join(self.mem, *parts)

    def test_blocks_new_fact_without_metadata_and_says_what_to_add(self):
        r = hook('Write', self.p('feedback_x.md'), '---\nname: a\n---\nbody')
        self.assertEqual(r.returncode, 2)
        self.assertIn('author:', r.stderr)
        self.assertIn('created:', r.stderr)

    def test_blocks_when_only_one_key_present(self):
        r = hook('Write', self.p('f.md'), '---\nmetadata:\n  author: owner\n---\n')
        self.assertEqual(r.returncode, 2)
        self.assertIn('created:', r.stderr)
        self.assertNotIn('author: <', r.stderr)
        self.assertEqual(hook('Write', self.p('g.md'), 'no frontmatter at all').returncode, 2)

    def test_passes_new_fact_with_metadata(self):
        self.assertEqual(hook('Write', self.p('feedback_x.md'), GOOD).returncode, 0)

    def test_passes_exempt_paths(self):
        for rel in (('MEMORY.md',), ('topics', 'ci.md'), ('library', 'reference', 'a', 'b.md')):
            self.assertEqual(hook('Write', self.p(*rel), '# no frontmatter').returncode, 0, rel)

    def test_passes_edit_of_existing_file(self):
        path = self.p('old.md')
        with open(path, 'w', encoding='utf-8') as fh:
            fh.write('legacy fact without metadata')
        self.assertEqual(hook('Write', path, 'rewritten, still no metadata').returncode, 0)

    def test_ignores_other_tools_and_non_memory_paths(self):
        self.assertEqual(hook('Edit', self.p('new.md'), '', name='Edit').returncode, 0)
        self.assertEqual(hook('Write', os.path.join(self.tmp, 'README.md'), 'x').returncode, 0)
        self.assertEqual(hook('Write', self.p('data.json'), '{}').returncode, 0)

    def test_dotdot_path_is_not_exempt(self):
        r = hook('Write', self.p('library', '..', 'evil.md'), 'no frontmatter')
        self.assertEqual(r.returncode, 2)

    def test_malformed_json_and_missing_file_path_fail_open(self):
        bad = subprocess.run([sys.executable, '-I', HOOK], input='{not json', capture_output=True, text=True)
        self.assertNotEqual(bad.returncode, 2)
        payload = json.dumps({'tool_name': 'Write', 'tool_input': {'content': 'x'}})
        r = subprocess.run([sys.executable, '-I', HOOK], input=payload, capture_output=True, text=True)
        self.assertNotEqual(r.returncode, 2)

    def test_backslash_path_to_new_fact_blocks(self):
        win = 'C:\\Users\\u\\.claude\\projects\\p\\memory\\feedback_x.md'
        self.assertEqual(hook('Write', win, 'no frontmatter').returncode, 2)
        self.assertEqual(hook('Write', win, GOOD).returncode, 0)
        exempt = 'C:\\Users\\u\\.claude\\projects\\p\\memory\\topics\\t.md'
        self.assertEqual(hook('Write', exempt, 'x').returncode, 0)

    def test_hooks_json_points_at_the_script(self):
        path = os.path.join(os.path.dirname(os.path.dirname(SKILL)), 'hooks', 'hooks.json')
        with open(path, encoding='utf-8') as fh:
            cfg = json.load(fh)
        h = cfg['hooks']['PreToolUse'][0]
        self.assertEqual(h['matcher'], 'Write')
        arg = h['hooks'][0]['args'][-1]
        self.assertTrue(os.path.isfile(arg.replace('${CLAUDE_PLUGIN_ROOT}', os.path.dirname(os.path.dirname(SKILL)))))


if __name__ == '__main__':
    unittest.main()
