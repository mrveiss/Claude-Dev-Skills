When to use: Reading the fork/duplicate report, or turning one class of forks into one issue and one fix.

# /claude-dev-skills:code-library forks

`scripts/forks.py` writes `library/forks/REPORT.md`: one entry per class (one concept, all its homes). Read-only; it never runs a scanner from the target repo.

| Section | Rule | Verdict |
|---|---|---|
| same symbol | top-level class, function or constant name in 2+ Python modules | identical bodies/values = DUPLICATE, differing = FORK |
| same file name | a `.py` file name in 2+ directories (common names are skipped) | identical text = DUPLICATE, differing = FORK |
| near-duplicate | function bodies equal after erasing names and literals, bucketed by hash (never compared pairwise); a bucket must span 2+ files and hold at least `--min-nodes` AST nodes | NEAR-DUPLICATE |
| audit (`--audit`) | a canonical-audit JSON (array of diagnostics with `rule_id`, `issue`, `file`, `line`) grouped by rule; rules hitting a class home are named on its entry | as the audit says |

Headline rule (applies to every section): a class is shown only if at least 1 home is consumed (its symbol is imported by name from another module, `from m import NAME`, resolved by text; for a same-file-name class, any import of the module) AND at least 2 homes are non-script modules (a script has an `if __name__ == "__main__"` guard or is `__main__.py`). Every other class is one collapsed line, `local, not consumed: N classes`; `--all` lists them in a final section.

Without `--audit` the report says so in one line; the audit's producing workflow is currently failing (AutoBot-AI#21689), so the report works without it.
Each entry gives: concept, homes as `file:line`, proposed home with the reason, importers to migrate, and the matching issue from `--issues` (a `gh issue list --json number,title,body,state` dump you save yourself; the script never calls gh) or "no issue yet".

Proposed home, by layering: primitive (shared, lib, utils, common) -> orchestrator (service, workflow, anything else) -> agent. The lowest layer that already defines the concept wins; within a layer the most-imported home wins; then the first path. The layer globs are in `code-classes.json`.

Turning a class into work (one defect, one fix):
1. Take one report entry. If it has a matching issue, link to that issue and add the sighting there; do not open a second.
2. No issue yet: file one for the class, listing every home and the importers to migrate; native sub-issue and `blocked_by` links follow your project's issue rules.
3. Fix it once: migrate each importer to the proposed home, then remove the other homes only after the importers are moved and the change has landed.
4. A FORK is a decision first (which behaviour is right); a DUPLICATE is mechanical. The proposed home is a default, not a verdict: check the reason line and the importer counts before moving code.
5. Regenerate the map for the new commit; the class should be gone from the report.

The report is a candidate list, not proof: same names can be unrelated (check the homes), and the importer lists are text-resolved estimates.
