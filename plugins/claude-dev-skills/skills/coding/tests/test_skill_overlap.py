"""Tests for skill_overlap.py using fixture skills built in a temp dir."""
import io
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'scripts'))
import skill_overlap  # noqa: E402

SHARED = ('Always read the existing helper before writing a new one, because a second copy of the same '
          'logic drifts and nobody can tell which copy is current.')


def make_skill(root, name, body):
    d = Path(root) / 'skills' / name
    (d / 'references').mkdir(parents=True)
    (d / 'SKILL.md').write_text('---\nname: %s\ndescription: x\n---\n\n# %s\n\n%s\n' % (name, name, body),
                                encoding='utf-8')
    return d


def run(*args):
    out = io.StringIO()
    with redirect_stdout(out):
        code = skill_overlap.main(list(args))
    return code, out.getvalue()


class SkillOverlapTest(unittest.TestCase):
    def test_overlapping_pair_reported_with_both_locations(self):
        with tempfile.TemporaryDirectory() as t:
            make_skill(t, 'alpha', SHARED)
            make_skill(t, 'beta', SHARED.replace('Always', 'Always,'))
            code, out = run(t)
            self.assertEqual(code, 1)
            self.assertIn('alpha/SKILL.md:8', out)
            self.assertIn('beta/SKILL.md:8', out)
            self.assertIn('1 finding(s)', out)

    def test_clean_pair_not_reported(self):
        with tempfile.TemporaryDirectory() as t:
            make_skill(t, 'alpha', SHARED)
            make_skill(t, 'beta', 'Measure twice and cut once, then check every edge against the square '
                                  'before the glue goes on and the clamps come out.')
            code, out = run(t)
            self.assertEqual(code, 0)
            self.assertIn('0 finding(s)', out)

    def test_same_skill_frontmatter_and_fences_ignored(self):
        with tempfile.TemporaryDirectory() as t:
            fence = '```\n%s\n```' % SHARED
            make_skill(t, 'alpha', SHARED + '\n\n' + SHARED)  # repeat inside one skill: not an overlap
            make_skill(t, 'beta', fence)  # same text but in a code fence: skipped
            code, _ = run(t)
            self.assertEqual(code, 0)

    def test_does_not_modify_files(self):
        with tempfile.TemporaryDirectory() as t:
            d = make_skill(t, 'alpha', SHARED)
            make_skill(t, 'beta', SHARED)
            before = (d / 'SKILL.md').read_bytes()
            run(t)
            self.assertEqual(before, (d / 'SKILL.md').read_bytes())

    def test_similarity_bounds_and_empty_inputs(self):
        self.assertEqual(skill_overlap.similarity(' ', '', 0.85), 0.0)
        self.assertEqual(skill_overlap.similarity('a b c', 'x y z w v u t s r q', 0.85), 0.0)
        self.assertEqual(skill_overlap.similarity('same words here', 'same words here', 0.85), 1.0)


if __name__ == '__main__':
    unittest.main()
