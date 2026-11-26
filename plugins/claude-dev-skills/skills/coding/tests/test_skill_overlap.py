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

    def test_invocation_lines_differing_only_by_own_name_not_reported(self):
        line = 'Invoke as `/my-plugin:%s [args]`; no argument means apply it to the situation.'
        with tempfile.TemporaryDirectory() as t:
            make_skill(t, 'alpha-one', line % 'alpha-one')
            make_skill(t, 'beta-two', line % 'beta-two')
            code, out = run(t)
            self.assertEqual(code, 0)
            self.assertIn('0 finding(s)', out)

    def test_rule_next_to_own_command_still_reported(self):
        rule = ('Always read the existing helper before writing a new one, because a second copy of the '
                'same logic drifts and nobody can tell which copy is current in this repository.')
        with tempfile.TemporaryDirectory() as t:
            make_skill(t, 'alpha', 'Use `/p:alpha [args]` now. ' + rule)
            make_skill(t, 'beta', 'Use `/p:beta [args]` now. ' + rule)
            code, out = run(t)
            self.assertEqual(code, 1)
            self.assertIn('1 finding(s)', out)

    def test_bare_slash_name_is_not_a_command(self):
        line = 'For anything about quality of the change, see /%s before you ask for a second opinion.'
        with tempfile.TemporaryDirectory() as t:
            make_skill(t, 'review', line % 'review')
            make_skill(t, 'other', line % 'review')
            self.assertEqual(run(t)[0], 1)

    def test_single_word_names_usage_line_not_reported(self):
        line = 'Invoke as `/my-plugin:%s [args]`; no argument means apply it to the situation.'
        with tempfile.TemporaryDirectory() as t:
            make_skill(t, 'alpha', line % 'alpha')
            make_skill(t, 'beta', line % 'beta')
            self.assertEqual(run(t)[0], 0)

    def test_real_shared_paragraph_with_names_still_reported(self):
        body = ('The %s skill must always read the existing helper before writing a new one, because a '
                'second copy of the same logic drifts and nobody can tell which copy is current.')
        with tempfile.TemporaryDirectory() as t:
            make_skill(t, 'alpha-one', body % 'alpha-one')
            make_skill(t, 'beta-two', body % 'beta-two')
            code, out = run(t)
            self.assertEqual(code, 1)
            self.assertIn('1 finding(s)', out)

    def test_within_skill_reports_reference_repeating_skill_md(self):
        with tempfile.TemporaryDirectory() as t:
            d = make_skill(t, 'alpha', SHARED)
            (d / 'references' / 'ref.md').write_text('# Ref\n\n%s\n' % SHARED, encoding='utf-8')
            self.assertEqual(run(t)[0], 0)  # default: same-skill pairs skipped
            code, out = run(t, '--within-skill')
            self.assertEqual(code, 1)
            self.assertIn('alpha/SKILL.md:8', out)
            self.assertIn('alpha/references/ref.md:3', out)

    def test_within_skill_reports_reference_vs_reference(self):
        with tempfile.TemporaryDirectory() as t:
            d = make_skill(t, 'alpha', 'Unrelated text about measuring twice and cutting once on every edge.')
            for n in ('a.md', 'b.md'):
                (d / 'references' / n).write_text('# R\n\n%s\n' % SHARED, encoding='utf-8')
            code, out = run(t, '--within-skill')
            self.assertEqual(code, 1)
            self.assertIn('1 finding(s)', out)

    def test_within_skill_does_not_pair_a_paragraph_with_itself(self):
        with tempfile.TemporaryDirectory() as t:
            make_skill(t, 'alpha', SHARED)
            self.assertEqual(run(t, '--within-skill')[0], 0)

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
