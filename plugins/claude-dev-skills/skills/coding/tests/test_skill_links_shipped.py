"""Every file a skill's markdown links to must exist and be tracked by git.

Regression for #20: memory-library's references/ matched the repo's
references/* ignore rule, so the merged skill linked to files that never shipped.
"""
import pathlib
import re
import subprocess
import unittest

REPO = pathlib.Path(__file__).resolve().parents[5]
SKILLS = REPO / "plugins"
# Fenced blocks are examples, never links. Outside them: a markdown link to a
# relative file (inline code removed first, since a link inside `...` is an example),
# or a backticked path into the skill's own references/ or scripts/ (paths elsewhere
# in backticks name the user's project, not the skill).
FENCE = re.compile(r"```.*?```", re.S)
CODE = re.compile(r"`[^`\n]*`")
MD_LINK = re.compile(r"\]\((?!https?:|#|/)((?:\./)?[\w./-]+\.\w+)\)")
SKILL_PATH = re.compile(r"`((?:\./)?(?:references|scripts)/[\w./-]+\.\w+)`")


def _links(text):
    """Relative file links a reader would follow in *text*."""
    text = FENCE.sub("", text)
    return set(MD_LINK.findall(CODE.sub("", text))) | set(SKILL_PATH.findall(text))


def _untracked(path):
    """True when *path* is not in the git index: ignored, or simply never added."""
    run = subprocess.run(["git", "-C", str(REPO), "ls-files", "--error-unmatch", str(path)],
                         check=False, capture_output=True)
    return run.returncode != 0


class SkillLinksShipped(unittest.TestCase):
    def test_linked_files_exist_and_are_not_ignored(self):
        problems = []
        for doc in SKILLS.glob("*/skills/*/**/*.md"):
            skill_dir = doc.relative_to(SKILLS).parts[:3]
            base = SKILLS.joinpath(*skill_dir)
            here = doc.parent
            for rel in _links(doc.read_text(encoding="utf-8")):
                rel = rel.rstrip(".,;:").removeprefix("./")
                target = base / rel if (base / rel).exists() or rel.startswith(("references/", "scripts/")) else here / rel
                if not target.exists():
                    problems.append(f"{doc.relative_to(REPO)} links missing {rel}")
                elif target.is_file() and _untracked(target):
                    problems.append(f"{doc.relative_to(REPO)} links untracked {rel}")
        self.assertEqual(problems, [])


if __name__ == "__main__":
    unittest.main()
