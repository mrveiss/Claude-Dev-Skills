---
name: commit
description: Standardized commit workflow with pre-flight checks, auto-format, and retry logic for pre-commit hooks
---

# /commit - Standardized Commit Workflow

## Pre-Flight
- `git branch --show-current` — wrong branch? STOP and ask user
- `git status && git diff --cached --stat` — review what will be committed
- Nothing staged? `git add -u` or add specific files

## Auto-Format Python (before committing)
```bash
STAGED_PY=$(git diff --cached --name-only --diff-filter=ACM | grep '\.py$')
if [ -n "$STAGED_PY" ]; then
  BLACK=$(command -v black)
  echo "$STAGED_PY" | tr '\n' '\0' | xargs -0 "$BLACK" --line-length=88 --quiet
  echo "$STAGED_PY" | tr '\n' '\0' | xargs -0 isort --profile black --quiet
  git add -u
fi
```

## Commit
```bash
git commit -m "<type>(scope): <description> (#<issue-number>)"
```
- Types: `feat`, `fix`, `chore`, `refactor`, `docs`, `style`, `test`
- Always include issue number
- **NEVER include `Co-Authored-By` trailer**

## Hook Retry (if commit fails due to reformatting)
```bash
git add -u && git commit -m "<same message>"
```
- Max 3 retries; if still failing after 3, stop and report

## Verify
- `git log -1 --stat` — confirm correct message and files

## CI Check (if PR exists)
```bash
gh pr checks
```
- Fix failures before marking issue `done`; never mark `done` with red CI

## Red Flags — STOP
- Wrong branch
- 3+ hook retry failures
- Unrelated changes mixed in one commit
