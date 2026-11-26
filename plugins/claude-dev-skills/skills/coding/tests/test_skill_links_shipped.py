"""Every file a SKILL.md links to must be tracked by git, not gitignored.

Regression for #20: memory-library's references/ matched the repo's
references/* ignore rule, so the merged skill linked to files that never shipped.
"""
import pathlib
import re
import subprocess
import unittest

REPO = pathlib.Path(__file__).resolve().parents[5]
SKILLS = REPO / "plugins"
LINK = re.compile(r"`?(references/[\w./-]+|scripts/[\w./-]+)`?")


def _ignored(path):
    """True when git would ignore *path* (check-ignore exits 0 on a match)."""
    run = subprocess.run(["git", "-C", str(REPO), "check-ignore", "-q", str(path)], check=False)
    return run.returncode == 0


class SkillLinksShipped(unittest.TestCase):
    def test_linked_files_exist_and_are_not_ignored(self):
        problems = []
        for skill_md in SKILLS.glob("*/skills/*/SKILL.md"):
            for rel in set(LINK.findall(skill_md.read_text(encoding="utf-8"))):
                target = skill_md.parent / rel.rstrip(".,;:")
                if not target.exists():
                    problems.append(f"{skill_md.relative_to(REPO)} links missing {rel}")
                elif _ignored(target):
                    problems.append(f"{skill_md.relative_to(REPO)} links gitignored {rel}")
        self.assertEqual(problems, [])


if __name__ == "__main__":
    unittest.main()
