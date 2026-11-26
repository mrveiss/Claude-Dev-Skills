"""Tests for code-library: map building, catalogues, forks, no-exec proof, output location, determinism, audit merge.

Run: python3 -m unittest discover -s plugins/claude-dev-skills/skills/code-library/tests -v
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

SKILL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(SKILL, 'scripts')
EXAMPLE = os.path.join(SKILL, 'references', 'code-classes.example.json')
sys.path.insert(0, SCRIPTS)
import _graph  # noqa: E402
import _scan  # noqa: E402
import forks  # noqa: E402
import index  # noqa: E402

SHA = 'abc1234def5678abc1234def5678abc1234def56'
DATE = '2026-11-27'
CONFIG = {
    'rooms': {'SA': {'dir': 'service-a', 'title': 'A', 'globs': ['svc_a/**']}, 'SB': {'dir': 'service-b', 'title': 'B', 'globs': ['svc_b/**']}},
    'shelves': {'API': {'name': 'api', 'room': 'SA', 'globs': ['svc_a/api/**']}, 'SHR': {'name': 'shared', 'room': 'SA', 'globs': ['svc_a/shared/**']}},
}
NEAR_A = '''def load_rows(db, limit):
    rows = []
    for r in db.fetch(limit):
        if r.ok and r.size > 3:
            rows.append((r.id, r.size * 2))
    total = sum(x[1] for x in rows)
    return rows, total
'''
NEAR_B = NEAR_A.replace('load_rows', 'read_entries').replace('rows', 'items').replace('> 3', '> 99').replace('* 2', '* 7')

FILES = {
    'svc_a/__init__.py': '',
    'svc_a/shared/__init__.py': '',
    'svc_a/shared/redis.py': 'TTL = 60\nMODE = "a"\n\n\ndef get_client():\n    return 1\n\n\nclass Store:\n    def put(self, k):\n        return k\n',
    'svc_a/api/__init__.py': '',
    'svc_a/api/routes.py': ('import os\nfrom fastapi import APIRouter\nfrom svc_a.shared.redis import get_client\n\nrouter = APIRouter(prefix="/v1")\n\n\n'
                            '@router.get("/items")\ndef list_items():\n    # tracked in #123\n    key = "cache:items"\n    return os.environ.get("APP_MODE"), get_client(), key\n\n\n'
                            'if __name__ == "__main__":\n    list_items()\n'),
    'svc_a/tests/test_api.py': 'from svc_a.api import routes\n\n\ndef test_x():\n    assert routes\n',
    'svc_b/__init__.py': '',
    'svc_b/agents/__init__.py': '',
    'svc_b/agents/worker.py': ('TTL = 60\nMODE = "b"\n\n\ndef get_client():\n    return 2\n\n\nclass Store:\n    def put(self, k):\n        return k\n\n\n'
                               '@scheduled("1h")\ndef sync_all():\n    return os.getenv("SYNC_URL")\n\n\n' + NEAR_A),
    'svc_b/workflow/__init__.py': '',
    'svc_b/workflow/flow.py': 'from svc_a.shared.redis import get_client\n\n\n' + NEAR_B + '\n\ndef run_flow():\n    return get_client()\n',
}
TRAP = 'import pathlib\npathlib.Path(__SENTINEL__).write_text("ran")\nraise RuntimeError("target code was imported")\n'


def make_repo(root, extra=None):
    for rel, text in {**FILES, **(extra or {})}.items():
        p = os.path.join(root, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, 'w', encoding='utf-8') as fh:
            fh.write(text)


def slurp(path):
    with open(path, encoding='utf-8') as fh:
        return fh.read()


def tree_hash(root):
    out = {}
    for base, _, files in os.walk(root):
        for f in files:
            p = os.path.join(base, f)
            with open(p, 'rb') as fh:
                out[os.path.relpath(p, root)] = hashlib.sha256(fh.read()).hexdigest()
    return out


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.repo, self.out = os.path.join(self.tmp, 'repo'), os.path.join(self.tmp, 'out')
        os.makedirs(self.repo)
        make_repo(self.repo)
        self.cfg = os.path.join(self.tmp, 'code-classes.json')
        with open(self.cfg, 'w', encoding='utf-8') as fh:
            json.dump(CONFIG, fh)

    def build(self, **kw):
        return index.build(self.repo, self.out, SHA, DATE, self.cfg, **kw)

    def lib(self, *parts):
        return os.path.join(self.out, 'library', *parts)

    def text(self, *parts):
        with open(self.lib(*parts), encoding='utf-8') as fh:
            return fh.read()

    def model(self):
        cls = _graph.Classifier(_graph.load_config(self.cfg))
        return cls, _graph.build_model(self.repo, cls)

    def report(self, audit=None, issues=None, min_nodes=20, show_all=True):
        cls, model = self.model()
        return forks.report(self.repo, SHA, model, cls, audit, issues, min_nodes, show_all)


class MapBuilding(Base):
    def test_rooms_shelves_and_card(self):
        stats = self.build()
        self.assertEqual(stats['domains'], 4)  # service-a api/shared/other, service-b other
        card = self.text('service-a', 'api', 'CARD.md')
        self.assertIn(f'commit: {SHA}', card)
        self.assertIn('GET /v1/items -> svc_a/api/routes.py:9 list_items', card)
        self.assertIn('CLI svc_a/api/routes.py', card)
        self.assertIn('- #123: svc_a/api/routes.py:10', card)
        self.assertIn('svc_a/tests/test_api.py', card)  # a test importing the domain
        self.assertIn('SA.API/map/card/2026-11-27', card)

    def test_scheduler_and_chapter(self):
        self.build()
        card = self.text('service-b', 'other', 'CARD.md')
        self.assertIn('scheduler svc_b/agents/worker.py:15 sync_all', card)
        chap = self.text('service-b', 'other', 'chapters', 'svc_b--agents--worker.md')
        self.assertIn('svc_b/agents/worker.py:5 get_client (function)', chap)
        self.assertIn(f'commit: {SHA}', chap)

    def test_every_card_carries_the_commit(self):
        self.build()
        for base, _, files in os.walk(self.lib()):
            for f in files:
                self.assertIn(f'commit: {SHA}', slurp(os.path.join(base, f)), f)

    def test_auto_rooms_without_config(self):
        index.build(self.repo, self.out, SHA, DATE, None)
        self.assertTrue(os.path.isfile(self.lib('svc_a', 'api', 'CARD.md')))

    def test_open_issues_filter(self):
        path = os.path.join(self.tmp, 'issues.json')
        with open(path, 'w', encoding='utf-8') as fh:
            json.dump([{'number': 123, 'state': 'CLOSED'}], fh)
        self.build(issues_path=path)
        self.assertIn('- none', self.text('service-a', 'api', 'CARD.md').split('## Issues cited')[1])


class Catalogues(Base):
    def test_lookups(self):
        self.build()
        self.assertIn('get_client | function | svc_a/shared/redis.py:5 | SA.SHR/map/svc_a--shared--redis/2026-11-27', self.text('catalog', 'concepts', 'g.md'))
        self.assertIn('/v1/items GET | list_items | svc_a/api/routes.py:9', self.text('catalog', 'routes.md'))
        self.assertIn('APP_MODE | svc_a/api/routes.py:12', self.text('catalog', 'env.md'))
        self.assertIn('SYNC_URL | svc_b/agents/worker.py', self.text('catalog', 'env.md'))
        self.assertIn('cache:items | svc_a/api/routes.py:11', self.text('catalog', 'keys.md'))
        self.assertIn('#123 | svc_a/api/routes.py:10', self.text('catalog', 'issues.md'))

    def test_tests_are_not_concepts(self):
        self.build()
        self.assertNotIn('test_x', self.text('catalog', 'concepts', 't.md'))


class Forks(Base):
    def entry(self, concept):
        text, classes = self.report()
        part = text.split(f'`{concept}` - ')[1].split('###')[0]
        return part

    def test_fork_vs_duplicate(self):
        self.assertTrue(self.entry('get_client').startswith('FORK'))
        self.assertTrue(self.entry('Store').startswith('DUPLICATE'))
        self.assertTrue(self.entry('TTL').startswith('DUPLICATE'))
        self.assertTrue(self.entry('MODE').startswith('FORK'))

    def test_layering_lowest_layer_wins(self):
        part = self.entry('get_client')
        self.assertIn('proposed home: svc_a/shared/redis.py:5 - layer primitive is the lowest of', part)

    def test_importers_to_migrate(self):
        text, _ = self.report()
        part = text.split('`get_client` - ')[1].split('###')[0]
        self.assertIn('importers to migrate: none found', part)  # the agent copy has no importer; the primitive is the canonical one

    def test_same_layer_most_imported_wins(self):
        extra = {'svc_b/workflow/other.py': 'def helper():\n    return 1\n', 'svc_b/workflow/third.py': 'def helper():\n    return 2\n',
                 'svc_b/workflow/user.py': 'from svc_b.workflow.third import helper\n'}
        make_repo(self.repo, extra)
        text, _ = self.report()
        self.assertIn('proposed home: svc_b/workflow/third.py:1 - layer orchestrator (same layer for all homes); most imported (1 importers)', text)

    def test_same_file_name_fork_and_duplicate(self):
        make_repo(self.repo, {'svc_a/shared/scan_dups.py': 'def one():\n    return 1\n', 'svc_b/agents/scan_dups.py': 'class Other:\n    pass\n',
                              'svc_a/shared/same.py': 'X_1 = 1\n', 'svc_b/agents/same.py': 'X_1 = 1\n'})
        self.assertTrue(self.entry('scan_dups.py').startswith('FORK'))
        self.assertTrue(self.entry('same.py').startswith('DUPLICATE'))
        self.assertNotIn('`__init__.py`', self.report()[0])  # common names are skipped

    def test_migration_paths_are_not_forks(self):
        make_repo(self.repo, {'svc_a/migrations/v1.py': 'def step():\n    return 1\n', 'svc_b/migrations/v1.py': 'def step():\n    return 2\n'})
        self.assertNotIn('`step`', self.report()[0])

    def test_near_duplicate_bucket(self):
        text, classes = self.report()
        near = [c for c in classes if c['verdict'] == 'NEAR-DUPLICATE']
        self.assertEqual(len(near), 1)
        self.assertEqual({r for r, _ in near[0]['homes']}, {'svc_b/agents/worker.py', 'svc_b/workflow/flow.py'})
        self.assertIn('NEAR-DUPLICATE', text)

    def test_near_duplicate_needs_same_structure(self):
        make_repo(self.repo, {'svc_b/workflow/flow.py': NEAR_B.replace('r.ok and ', '') })
        _, classes = self.report()
        self.assertEqual([c for c in classes if c['verdict'] == 'NEAR-DUPLICATE'], [])

    def test_issue_match_or_no_issue_yet(self):
        issues = [{'number': 77, 'title': 'Fork of get_client across services', 'body': '', 'state': 'OPEN'}]
        text, _ = self.report(issues=issues)
        self.assertIn('#77 Fork of get_client across services (OPEN)', text.split('`get_client` - ')[1].split('###')[0])
        self.assertIn('issue: no issue yet', text.split('`Store` - ')[1].split('###')[0])

    def test_without_audit_one_line(self):
        text, _ = self.report()
        self.assertEqual(text.count('audit: not merged'), 1)

    def test_audit_merge(self):
        audit = [{'rule_id': 'py_adhoc_redis', 'issue': '#555', 'severity': 'audit', 'file': 'svc_b/agents/worker.py', 'line': 5, 'message': 'm'},
                 {'rule_id': 'py_adhoc_redis', 'issue': '#555', 'severity': 'audit', 'file': 'svc_x/y.py', 'line': 1, 'message': 'm'},
                 {'not': 'a diagnostic'}]
        path = os.path.join(self.tmp, 'audit.json')
        with open(path, 'w', encoding='utf-8') as fh:
            json.dump(audit, fh)
        loaded = forks.load_audit(path)
        self.assertEqual(len(loaded), 2)
        text, _ = self.report(audit=loaded, issues=[{'number': 555, 'title': 'py_adhoc_redis cleanup', 'state': 'OPEN'}])
        self.assertNotIn('audit: not merged', text)
        self.assertIn('audit: merged 2 diagnostic(s)', text)
        self.assertIn('- py_adhoc_redis: 2 finding(s); issue ref #555', text)
        self.assertIn('audit rules hitting these homes: py_adhoc_redis', text.split('`get_client` - ')[1].split('###')[0])
        self.assertIn('issue: #555 (OPEN)', text)

    def test_cli_writes_report(self):
        run = subprocess.run([sys.executable, '-B', '-I', os.path.join(SCRIPTS, 'forks.py'), self.repo, self.out, '--config', self.cfg, '--commit', SHA],
                             capture_output=True, text=True)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertTrue(os.path.isfile(self.lib('forks', 'REPORT.md')))


class ConsumedFilter(Base):
    def test_unconsumed_classes_collapse(self):
        text, classes = self.report(show_all=False)
        self.assertIn('`get_client` - FORK', text)  # imported by name from the shared home
        self.assertNotIn('`Store` - ', text)
        self.assertNotIn('`TTL` - ', text)
        self.assertRegex(text, r'local, not consumed: \d+ classes \(rerun with --all to list them\)')
        self.assertTrue(any(c['concept'] == 'Store' and not c['headline'] for c in classes))

    def test_all_lists_the_local_ones(self):
        text, _ = self.report(show_all=True)
        self.assertIn('## Local, not consumed', text)
        self.assertIn('`Store` - DUPLICATE', text)

    def test_script_homes_do_not_count(self):
        make_repo(self.repo, {'svc_b/tools/a.py': 'def helper():\n    return 1\n\n\nif __name__ == "__main__":\n    helper()\n',
                              'svc_b/tools/b.py': 'def helper():\n    return 2\n',
                              'svc_b/tools/use.py': 'from svc_b.tools.b import helper\n'})
        text, _ = self.report(show_all=False)
        self.assertNotIn('`helper` - ', text)  # only one home is a non-__main__ module
        make_repo(self.repo, {'svc_b/tools/a.py': 'def helper():\n    return 1\n'})
        self.assertIn('`helper` - FORK', self.report(show_all=False)[0])


class Safety(Base):
    def test_symlinked_library_into_repo_is_refused(self):
        os.makedirs(self.out)
        os.symlink(os.path.join(self.repo, 'svc_a'), os.path.join(self.out, 'library'))
        before = tree_hash(self.repo)
        for script in ('index.py', 'forks.py'):
            run = subprocess.run([sys.executable, '-B', '-I', os.path.join(SCRIPTS, script), self.repo, self.out], capture_output=True, text=True)
            self.assertEqual(run.returncode, 2, run.stderr)
            self.assertIn('refusing to write inside the target repo', run.stderr)
        self.assertEqual(tree_hash(self.repo), before)

    def test_symlinked_subdir_into_repo_is_refused_before_any_write(self):
        os.makedirs(self.lib())
        os.symlink(os.path.join(self.repo, 'svc_b'), self.lib('service-b'))
        before = tree_hash(self.repo)
        with self.assertRaises(SystemExit) as cm:
            self.build()
        self.assertEqual(cm.exception.code, 2)
        self.assertEqual(tree_hash(self.repo), before)
        self.assertFalse(os.path.exists(self.lib('INDEX.md')))

    def test_deep_nesting_is_skipped_not_fatal(self):
        deep = 'def big():\n    return ' + ' + '.join(['1'] * 6000) + '\n\n\ndef ok():\n    return 1  # see #321\n'
        make_repo(self.repo, {'svc_a/deep.py': deep})
        stats = self.build()
        self.assertEqual(stats['skipped'], 1)
        self.assertIn('skipped: svc_a/deep.py (too deep)', self.text('INDEX.md'))
        self.assertIn('#321 | svc_a/deep.py:6', self.text('catalog', 'issues.md'))
        self.assertTrue(os.path.isfile(self.lib('service-a', 'api', 'CARD.md')))

    def test_commit_cannot_be_an_option(self):
        marker = os.path.join(self.tmp, 'o')
        for bad in ('--output=' + marker, '-x', '', 'a b'):
            with self.assertRaises(SystemExit) as cm:
                _graph.git_head(self.repo, bad)
            self.assertEqual(cm.exception.code, 2)
        run = subprocess.run([sys.executable, '-B', '-I', os.path.join(SCRIPTS, 'index.py'), self.repo, self.out, '--commit=--output=' + marker],
                             capture_output=True, text=True)
        self.assertEqual(run.returncode, 2)
        self.assertFalse(os.path.exists(marker))
        self.assertEqual(_graph.git_head(self.repo, 'deadbeef' * 5), ('unknown', 'unknown'))


    def test_target_code_is_never_imported_or_run(self):
        sentinel = os.path.join(self.tmp, 'sentinel')
        make_repo(self.repo, {'svc_a/trap.py': TRAP.replace('__SENTINEL__', repr(sentinel)), 'svc_a/conftest.py': TRAP.replace('__SENTINEL__', repr(sentinel)),
                              'svc_a/sitecustomize.py': TRAP.replace('__SENTINEL__', repr(sentinel))})
        before_path, before_mods = list(sys.path), set(sys.modules)
        self.build()
        cls, model = self.model()
        forks.report(self.repo, SHA, model, cls, None, None, 20, True)
        self.assertFalse(os.path.exists(sentinel))
        self.assertEqual(sys.path, before_path)
        self.assertFalse({m for m in set(sys.modules) - before_mods if m.split('.')[0] in ('svc_a', 'svc_b', 'trap')})
        run = subprocess.run([sys.executable, '-B', '-I', os.path.join(SCRIPTS, 'index.py'), self.repo, self.out + '2', '--config', self.cfg],
                             capture_output=True, text=True)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertFalse(os.path.exists(sentinel))
        self.assertIn('files: 14', self.text('INDEX.md'))  # the trap files were counted (read as text), not imported

    def test_syntax_error_files_are_survived(self):
        make_repo(self.repo, {'svc_a/broken.py': 'def (:\n    # see #999\n'})
        self.build()
        self.assertIn('#999 | svc_a/broken.py:2', self.text('catalog', 'issues.md'))

    def test_output_inside_repo_is_refused(self):
        run = subprocess.run([sys.executable, '-B', '-I', os.path.join(SCRIPTS, 'index.py'), self.repo, os.path.join(self.repo, 'map')],
                             capture_output=True, text=True)
        self.assertEqual(run.returncode, 2)
        self.assertIn('refusing to write inside the target repo', run.stderr)
        self.assertFalse(os.path.exists(os.path.join(self.repo, 'map')))
        run = subprocess.run([sys.executable, '-B', '-I', os.path.join(SCRIPTS, 'forks.py'), self.repo, self.repo], capture_output=True, text=True)
        self.assertEqual(run.returncode, 2)

    def test_repo_tree_is_unchanged_by_a_build(self):
        before = tree_hash(self.repo)
        self.build()
        forks.main([self.repo, self.out, '--config', self.cfg, '--commit', SHA])
        self.assertEqual(tree_hash(self.repo), before)


class Deterministic(Base):
    def test_same_commit_same_bytes(self):
        self.build()
        first = tree_hash(self.out)
        shutil.rmtree(self.out)
        self.build()
        self.assertEqual(tree_hash(self.out), first)

    def test_stale_generated_chapters_are_pruned(self):
        self.build()
        os.remove(os.path.join(self.repo, 'svc_b', 'workflow', 'flow.py'))
        self.build()
        self.assertFalse(os.path.exists(self.lib('service-b', 'other', 'chapters', 'svc_b--workflow--flow.md')))


class Config(unittest.TestCase):
    def test_example_config_loads_and_globs(self):
        cls = _graph.Classifier(_graph.load_config(EXAMPLE))
        self.assertTrue(cls.rooms)
        self.assertTrue(_graph.Globs(['a/**/b.py']).match('a/x/y/b.py'))
        self.assertTrue(_graph.Globs(['a/**/b.py']).match('a/b.py'))
        self.assertFalse(_graph.Globs(['a/*.py']).match('a/x/b.py'))

    def test_frontend_parse(self):
        rec = _scan.parse_frontend("import { a } from './a'\nexport function foo() {}\nexport const BAR = import.meta.env.VITE_X // #4242\n")
        self.assertEqual([d['name'] for d in rec['defs']], ['foo', 'BAR'])
        self.assertEqual(rec['env'], {'VITE_X': 3})
        self.assertEqual(rec['issues'], {4242: 3})
        self.assertEqual(rec['imports'][0]['module'], './a')


if __name__ == '__main__':
    unittest.main()
