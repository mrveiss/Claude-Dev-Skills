When to use: After completing a batch fix or implementation, audit adjacent files for the same issue and file GitHub discovery issues for each gap found. Use after any batch implementation, bug fix, or remediation campaign.

# Gap Audit

Run after completing work to catch similar issues in adjacent files that weren't part of the original batch.

## Steps

1. **Identify modified files from the completed work**
   ```bash
   git diff --name-only HEAD~1..HEAD
   # or for a specific PR:
   gh pr diff <PR_NUMBER> --name-only
   ```

2. **State the fix pattern in one sentence** — e.g., "adds response_model=None to router decorators", "adds source_id ownership guard to analytics endpoints", "adds --exclude=.env to rsync calls".

3. **Sweep repo-wide by behaviour** — search for the sink, call or pattern the fix addresses, not the file extension or the fixed directories; siblings, other services and shared helpers are in scope:
   ```bash
   grep -rnE "<sink-or-pattern>" . --include="*.<ext>" | grep -v __pycache__
   ```
   Record the exact command and its hit count in the report — a zero is "searched, none" only with the command shown. Drop already-fixed files.
   Fixed defect in a known family? Also run its checklist:
   - **Parsers** — every parse of untrusted input: size/depth limits, entity or external-reference handling, error path.
   - **Deserialisation / object construction** — every loader or constructor taking external data: unsafe loaders, type/class chosen by input.
   - **Archive extract / import / restore** — member-path containment, links, size and count limits, overwrite of existing data.
   - **Path join / containment** — every join with external input: `..`, absolute segments, symlinks, resolve-then-compare.
   - **Subprocess argv** — every spawn: shell use, argv vs string, option injection (`--`), env passthrough.

4. **Check each candidate** — for each file NOT in the already-fixed list:
   - Read the file
   - Apply the same fix criteria used in the completed work
   - If the same issue exists → add to gap list with specific line numbers

5. **File ONE issue per defect class** — one root cause, one issue, one fix. Every instance is a separately addressable `file:line` row; a safe sibling is evidence only for itself. First search for an existing class issue (`gh issue list --search "<pattern>" --state all`) and add instances there instead of filing a new one:
   ```bash
   gh issue create \
     --title "Gap: <fix-pattern> needed in <file-or-module>" \
     --body "$(cat <<'EOF'
   ## Discovered Gap

   **Pattern:** <what needs fixing>
   **Found during:** gap audit after <PR/commit reference>
   **Sweep:** `<search command>` — <hit count> hits

   ### Instances
   - [ ] `path/to/file.py:<N>` — <specific issue>

   ### Fix
   Apply the same fix as in <reference PR/commit>.

   **Estimated effort:** small
   EOF
   )" \
     --label "discovered,gap"
   ```

   Then attach it natively — a prose "found during #N" is not a relationship:
   ```bash
   gh api -X POST repos/$REPO/issues/$UMBRELLA/sub_issues \
     -F sub_issue_id=$(gh api repos/$REPO/issues/$NEW -q .id)
   ```

6. **Report** — output a summary:
   - Sweep command(s) and hit count(s)
   - Total candidates checked
   - Gaps found (with issue numbers filed)
   - Confirmation that no gaps = coverage complete

## Scope Heuristics

- **Default:** repo-wide behaviour sweep (Step 3), never only the fixed directories
- **API endpoint fix:** Scope to `api/` and `tests/api/` directories
- **Shared utility fix:** Check all importers (`grep -r "from module import"`)

## Example Invocation

> "I just fixed source_id guards in 3 analytics endpoints. Run a gap audit."

1. `git diff --name-only HEAD~3..HEAD` → lists `api/analytics_quality.py`, `api/analytics_code.py`, `api/analytics_cfg.py`
2. Pattern: "missing source_id ownership check before returning data"
3. Sweep repo-wide for the behaviour (e.g. every route returning analytics data), record command and hit count → check each hit
4. Found gap in `api/analytics_debt.py` → file issue
5. Report: "1 gap found, filed as #9234. 4 other analytics files clean."
