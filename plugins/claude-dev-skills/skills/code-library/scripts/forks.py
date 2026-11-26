#!/usr/bin/env python3
"""Report forks and duplicates, one entry per class (concept, all homes, canonical home, importers, issue). Read-only.

usage: python3 -I forks.py <repo> <out> [--audit canonical-audit.json] [--issues gh-issues.json]
                           [--commit SHA] [--commit-date D] [--config code-classes.json] [--min-nodes N] [--all]

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


def named_importers(model, home, name):
    """Files that import `name` BY NAME from home (`from m import name`, text-resolved); module-style imports do not count."""
    res = model['resolver']
    return sorted(i for i in model['importers'].get(home, [])
                  if model['files'][i]['lang'] == 'py'
                  and any(imp['name'] == name and home in res.python(i, imp) for imp in model['files'][i]['imports']))


def consumed_homes(model, e):
    """Homes whose symbol is imported by name elsewhere; a module-file class counts any import of the module."""
    out = []
    for h in e['defs']:
        name = h.get('sym', e['sym']).split('.')[0]
        users = symbol_importers(model, h['rel'], name) if h['kind'] == 'module' else named_importers(model, h['rel'], name)
        if users:
            out.append(h['rel'])
    return out


def is_script(model, rel):
    rec = model['files'][rel]
    return rec['cli'] or os.path.basename(rel) == '__main__.py'


def classify_headline(model, e):
    """Headline when 1+ home is consumed AND 2+ homes are not script (`__main__`) modules; else local, not consumed."""
    e['consumed'] = consumed_homes(model, e)
    e['headline'] = bool(e['consumed']) and sum(not is_script(model, h['rel']) for h in e['defs']) >= 2
    return e['headline']


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
        homes = [{'rel': r, 'line': m['line'], 'kind': 'function', 'layer': cls.layer(r), 'sym': m['name']} for r, m in members]
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


def section(title, entries, n, model, issues, audit_files):
    body = f'## {title}\n\n'
    for e in entries:
        n += 1
        body += render_entry(n, e, model, issues, audit_files) + '\n'
    return body, n


def report(repo, sha, model, cls, audit, issues, min_nodes, show_all=False):
    groups = [('Same symbol in 2+ modules', symbol_classes(model, cls)), ('Same file name in 2+ directories', file_classes(model, cls)),
              ('Near-duplicate function bodies', near_classes(model, cls, min_nodes))]
    key = lambda e: (-len(e['homes']), e['concept'])  # noqa: E731
    audit_files = collections.defaultdict(set)
    for d in audit or []:
        audit_files[str(d.get('file', '')).replace(os.sep, '/')].add(d['rule_id'])
    for _, g in groups:
        for e in g:
            classify_headline(model, e)
    every = sorted((e for _, g in groups for e in g), key=key)
    head_n = sum(e['headline'] for e in every)
    local = [e for e in every if not e['headline']]
    count = lambda v: sum(e['verdict'] == v for e in every if e['headline'])  # noqa: E731
    head = (f'{MARK}\n# Fork and duplicate report\n\ncommit: {sha}\n\nheadline classes: {head_n} ({count("FORK")} fork, '
            f'{count("DUPLICATE")} duplicate, {count("NEAR-DUPLICATE")} near-duplicate)\n'
            f'local, not consumed: {len(local)} classes' + (' (listed below)' if show_all else ' (rerun with --all to list them)') + '\n'
            'a class is one concept with all its homes: one issue, one fix per class\n\n')
    head += (NO_AUDIT + '\n\n') if audit is None else f'audit: merged {len(audit)} diagnostic(s)\n\n'
    body, n = '', 0
    for title, g in groups:
        text, n = section(title, sorted((e for e in g if e['headline']), key=key), n, model, issues, audit_files)
        body += text
    if show_all:
        text, n = section('Local, not consumed', sorted(local, key=key), n, model, issues, audit_files)
        body += text
    if audit:
        body += '## Audit findings by rule\n\n'
        for rule, ds in audit_by_rule(audit).items():
            top = collections.Counter(str(d.get('file')) for d in ds).most_common(5)
            body += f'- {rule}: {len(ds)} finding(s); issue ref {ds[0].get("issue", "?")}; top files: ' + ', '.join(f'{f} x{c}' for f, c in top) + '\n'
            hits = match_issues({'sym': rule, 'homes': [(str(d.get('file')), 0) for d in ds]}, issues)
            if hits is not None:
                body += '  - issue: ' + ('; '.join(f'#{h["number"]} ({h.get("state", "?")})' for h in hits) or 'no issue yet') + '\n'
    return head + body, every


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
    ap.add_argument('--all', action='store_true', help='also list the local, not consumed classes')
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
    text, classes = report(repo, sha, model, cls, audit, issues, a.min_nodes, a.all)
    path = os.path.join(out, 'library', 'forks', 'REPORT.md')
    _graph.guard_paths(repo, [path])
    _lib.write_text(out, path, text)
    print(f'fork report for {sha}: {sum(c["headline"] for c in classes)} headline of {len(classes)} classes; ' + ('audit merged' if audit is not None else NO_AUDIT))


if __name__ == '__main__':
    main()
