#!/usr/bin/env python3
"""Report forks and duplicates, one entry per class (concept, all homes, canonical home, importers, issue). Read-only.

usage: python3 -I forks.py <repo> <out> [--audit canonical-audit.json] [--issues gh-issues.json]
                           [--commit SHA] [--commit-date D] [--config code-classes.json] [--min-nodes N]

(a) same top-level Python symbol in 2+ modules: differing bodies = FORK, identical = DUPLICATE;
(a2) same Python file name in 2+ directories, same verdict rule (a copied module that diverged);
(b) near-duplicate function bodies (names and literals erased), bucketed by hash;
(c) --audit: a canonical-audit JSON (array of diagnostics) is merged; without it the report says so.
Writes <out>/library/forks/REPORT.md (never inside <repo>). Parses text only; never runs repo code.
"""
import argparse
import collections
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _graph  # noqa: E402
from _graph import MARK, LAYERS, _lib  # noqa: E402

MIN_NODES = 30
NO_AUDIT = 'audit: not merged (no --audit given; its producing workflow is failing, AutoBot-AI#21689)'


def shared_symbols(model, cls):
    """{name: [home]} for python symbols defined in 2+ distinct non-test modules (names in cls.ignore skipped)."""
    by = collections.defaultdict(dict)
    for rel, rec in sorted(model['files'].items()):
        if rec['test'] or rec['lang'] != 'py' or cls.fork_skip.match(rel):
            continue
        for d in rec['defs']:
            n = d['name']
            if n in cls.ignore or (n.startswith('__') and n.endswith('__')):
                continue
            by[n].setdefault(rel, {'rel': rel, 'line': d['line'], 'kind': d['kind'], 'hash': d['hash'], 'layer': cls.layer(rel)})
    return {n: [h for _, h in sorted(v.items())] for n, v in sorted(by.items()) if len(v) >= 2}


def symbol_importers(model, home, name):
    """Files importing `name` (or its module) from home: text-resolved, an estimate."""
    res, out = model['resolver'], []
    for imp_rel in model['importers'].get(home, []):
        rec = model['files'][imp_rel]
        for imp in rec['imports']:
            if rec['lang'] == 'py' and (imp['name'] in (name, None) or imp['name'] == home.rsplit('/', 1)[-1][:-3]) \
                    and home in res.python(imp_rel, imp):
                out.append(imp_rel)
                break
            if rec['lang'] != 'py' and home in res.frontend(imp_rel, imp):
                out.append(imp_rel)
                break
    return sorted(out)


def propose(model, homes, name):
    """Lowest layer already defining it wins (primitive < orchestrator < agent), then the most-imported, then path."""
    scored = []
    for h in homes:
        n = len(symbol_importers(model, h['rel'], name))
        scored.append((LAYERS.index(h['layer']), -n, h['rel'], h, n))
    scored.sort(key=lambda t: t[:3])
    best = scored[0]
    why = f'layer {best[3]["layer"]}'
    layers = {t[3]['layer'] for t in scored}
    if len(layers) > 1:
        why += f' is the lowest of {", ".join(sorted(layers, key=LAYERS.index))}'
    elif len(scored) > 1 and best[1] != scored[1][1]:
        why += f' (same layer for all homes); most imported ({best[4]} importers)'
    else:
        why += ' (same layer, tie on importers); first by path'
    return best[3], why, {t[3]['rel']: t[4] for t in scored}


def symbol_classes(model, cls):
    out = []
    for name, homes in shared_symbols(model, cls).items():
        hashes = {h['hash'] for h in homes}
        out.append({'concept': name, 'verdict': 'DUPLICATE' if len(hashes) == 1 else 'FORK', 'what': homes[0]['kind'],
                    'homes': [(h['rel'], h['line']) for h in homes], 'defs': homes, 'sym': name})
    return out


def near_classes(model, cls, min_nodes):
    buckets = collections.defaultdict(list)
    for rel, rec in sorted(model['files'].items()):
        if rec['test'] or rec['lang'] != 'py' or cls.fork_skip.match(rel):
            continue
        for m in rec['methods']:
            if m['nodes'] >= min_nodes:
                buckets[m['norm']].append((rel, m))
    out = []
    for members in buckets.values():
        if len({r for r, _ in members}) < 2:
            continue
        names = [m['name'] for _, m in members]
        if len(set(names)) == 1 and '.' not in names[0]:
            continue  # same top-level name: class (a) already reports it
        top = collections.Counter(names).most_common(1)[0][0]
        homes = [{'rel': r, 'line': m['line'], 'kind': 'function', 'layer': cls.layer(r)} for r, m in members]
        out.append({'concept': top, 'verdict': 'NEAR-DUPLICATE', 'what': f'{len(members)} bodies, names: ' + ', '.join(sorted(set(names))[:6]),
                    'homes': [(h['rel'], h['line']) for h in homes], 'defs': homes, 'sym': top.split('.')[-1]})
    return out


def file_classes(model, cls):
    """Same python file name in 2+ directories: identical text = DUPLICATE, else FORK (a copied-and-diverged module)."""
    by = collections.defaultdict(list)
    for rel, rec in sorted(model['files'].items()):
        stem = os.path.basename(rel)[:-3]
        if rec['test'] or rec['lang'] != 'py' or not rel.endswith('.py') or stem in cls.ignore_files or cls.fork_skip.match(rel):
            continue
        by[os.path.basename(rel)].append({'rel': rel, 'line': 1, 'kind': 'module', 'layer': cls.layer(rel), 'sha': rec['sha']})
    out = []
    for name, homes in sorted(by.items()):
        if len(homes) >= 2:
            out.append({'concept': name, 'verdict': 'DUPLICATE' if len({h['sha'] for h in homes}) == 1 else 'FORK', 'what': 'module file',
                        'homes': [(h['rel'], 1) for h in homes], 'defs': homes, 'sym': name[:-3]})
    return out


def match_issues(entry, issues):
    if not issues:
        return None
    pat = re.compile(r'(?<![\w])' + re.escape(entry['sym']) + r'(?![\w])')
    paths = {r for r, _ in entry['homes']}
    hits = [i for i in issues if pat.search(f'{i.get("title", "")} {i.get("body") or ""}')
            or any(p in (i.get('body') or '') for p in paths)]
    return sorted(hits, key=lambda i: int(i['number']))[:5]


def load_audit(path):
    with open(path, encoding='utf-8') as fh:
        data = json.load(fh)
    if isinstance(data, dict):
        data = data.get('diagnostics') or data.get('findings') or []
    return [d for d in data if isinstance(d, dict) and 'rule_id' in d]


def audit_by_rule(diags):
    g = collections.defaultdict(list)
    for d in diags:
        g[d['rule_id']].append(d)
    return dict(sorted(g.items()))


def render_entry(i, e, model, issues, audit_files):
    homes = ', '.join(f'{r}:{ln}' for r, ln in e['homes'])
    best, why, counts = propose(model, e['defs'], e['sym'])
    lines = [f'### {i}. `{e["concept"]}` - {e["verdict"]} ({len(e["homes"])} homes; {e["what"]})\n',
             f'- homes: {homes}\n', f'- proposed home: {best["rel"]}:{best["line"]} - {why}\n']
    mig = [(h['rel'], symbol_importers(model, h['rel'], e['sym'])) for h in e['defs'] if h['rel'] != best['rel']]
    lines.append('- importers to migrate: ' + ('; '.join(f'{r} <- {", ".join(v[:8])}{" ..." if len(v) > 8 else ""}' for r, v in mig if v) or 'none found') + '\n')
    hits = match_issues(e, issues)
    if hits is None:
        lines.append('- issue: not checked (no --issues given)\n')
    else:
        lines.append('- issue: ' + ('; '.join(f'#{h["number"]} {h.get("title", "")[:80]} ({h.get("state", "?")})' for h in hits) or 'no issue yet') + '\n')
    flagged = sorted({f'{rule}' for r, _ in e['homes'] for rule in audit_files.get(r, [])})
    if flagged:
        lines.append('- audit rules hitting these homes: ' + ', '.join(flagged) + '\n')
    return ''.join(lines)


def report(repo, sha, model, cls, audit, issues, min_nodes):
    classes = symbol_classes(model, cls)
    near = near_classes(model, cls, min_nodes)
    files = file_classes(model, cls)
    key = lambda e: (-len(e['homes']), e['concept'])  # noqa: E731
    audit_files = collections.defaultdict(set)
    for d in audit or []:
        audit_files[str(d.get('file', '')).replace(os.sep, '/')].add(d['rule_id'])
    head = (f'{MARK}\n# Fork and duplicate report\n\ncommit: {sha}\n\nclasses: {sum(c["verdict"] == "FORK" for c in classes)} fork, '
            f'{sum(c["verdict"] == "DUPLICATE" for c in classes)} duplicate, {len(near)} near-duplicate, {len(files)} same-file-name\n'
            'a class is one concept with all its homes: one issue, one fix per class\n\n')
    head += (NO_AUDIT + '\n\n') if audit is None else f'audit: merged {len(audit)} diagnostic(s)\n\n'
    body, n = '## Same symbol in 2+ modules\n\n', 0
    for e in sorted(classes, key=key):
        n += 1
        body += render_entry(n, e, model, issues, audit_files) + '\n'
    body += '## Same file name in 2+ directories\n\n'
    for e in sorted(files, key=key):
        n += 1
        body += render_entry(n, e, model, issues, audit_files) + '\n'
    body += '## Near-duplicate function bodies\n\n'
    for e in sorted(near, key=key):
        n += 1
        body += render_entry(n, e, model, issues, audit_files) + '\n'
    if audit:
        body += '## Audit findings by rule\n\n'
        for rule, ds in audit_by_rule(audit).items():
            top = collections.Counter(str(d.get('file')) for d in ds).most_common(5)
            body += f'- {rule}: {len(ds)} finding(s); issue ref {ds[0].get("issue", "?")}; top files: ' + ', '.join(f'{f} x{c}' for f, c in top) + '\n'
            hits = match_issues({'sym': rule, 'homes': [(str(d.get('file')), 0) for d in ds]}, issues)
            if hits is not None:
                body += '  - issue: ' + ('; '.join(f'#{h["number"]} ({h.get("state", "?")})' for h in hits) or 'no issue yet') + '\n'
    return head + body, sorted(classes + files + near, key=key)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('repo')
    ap.add_argument('out')
    ap.add_argument('--audit')
    ap.add_argument('--issues')
    ap.add_argument('--commit')
    ap.add_argument('--commit-date')
    ap.add_argument('--config')
    ap.add_argument('--min-nodes', type=int, default=MIN_NODES)
    a = ap.parse_args(argv)
    repo, out = os.path.abspath(a.repo), os.path.abspath(a.out)
    _graph.check_out_outside(repo, out)
    sha, _ = _graph.git_head(repo, a.commit or 'HEAD')
    sha = a.commit or sha
    cls = _graph.Classifier(_graph.load_config(a.config))
    model = _graph.build_model(repo, cls)
    issues = None
    if a.issues:
        with open(a.issues, encoding='utf-8') as fh:
            issues = json.load(fh)
    audit = load_audit(a.audit) if a.audit else None
    text, classes = report(repo, sha, model, cls, audit, issues, a.min_nodes)
    _lib.write_text(out, os.path.join(out, 'library', 'forks', 'REPORT.md'), text)
    print(f'fork report for {sha}: {len(classes)} classes; ' + ('audit merged' if audit is not None else NO_AUDIT))


if __name__ == '__main__':
    main()
