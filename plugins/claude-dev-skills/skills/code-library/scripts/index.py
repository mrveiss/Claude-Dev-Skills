#!/usr/bin/env python3
"""Build the read-only code map (rooms, domain cards, chapters, catalogues) for a repo at a commit.

usage: python3 -I index.py <repo> <out> [--commit SHA] [--commit-date YYYY-MM-DD] [--config code-classes.json] [--issues gh-issues.json]

Parses file TEXT only (ast / regex): never imports, runs or installs anything from <repo>.
Writes under <out>/library/, which must be outside <repo>. Deterministic for one commit.
"""
import argparse
import collections
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _graph  # noqa: E402
from _graph import MARK, AUTHOR, _lib  # noqa: E402

CAP = {'routes': 60, 'concepts': 60, 'keys': 25, 'tests': 30, 'issues': 30, 'sched': 20}


def header(title, sha, call):
    return f'{MARK}\n# {title}\n\ncommit: {sha}\ncall number: {call}\n\n'


def more(shown, total, where):
    return f'- ... {total - shown} more: see {where}\n' if total > shown else ''


def load_open_issues(path):
    if not path:
        return None
    with open(path, encoding='utf-8') as fh:
        data = json.load(fh)
    return {int(i['number']) for i in data if str(i.get('state', 'OPEN')).upper() == 'OPEN'}


def domains(model, cls):
    """{(room code, room dir, shelf code, shelf dir): [rel]} (test files kept: the card lists those importing the domain)."""
    out = collections.defaultdict(list)
    for rel in sorted(model['files']):
        out[cls.place(rel)].append(rel)
    return dict(sorted(out.items()))


def chapter_text(rel, rec, place, sha, date, importers):
    rc, _, sc, _ = place
    call = _lib.call_number(rc, sc, AUTHOR, _graph.slug_module(rel), date)
    lines = [header(f'Chapter {rel}', sha, call), f'{rec["lines"]} lines; imported by {len(importers)} file(s)\n\n## Symbols\n']
    lines += [f'- {rel}:{d["line"]} {d["name"]} ({d["kind"]})\n' for d in sorted(rec['defs'], key=lambda d: (d['line'], d['name']))]
    if rec['routes']:
        lines.append('\n## Routes\n')
        lines += [f'- {r["method"]} {r["path"]} -> {rel}:{r["line"]} {r["handler"]}\n' for r in rec['routes']]
    for title, key in (('Environment variables', 'env'), ('Redis keys', 'keys'), ('Tables', 'tables')):
        if rec[key]:
            lines.append(f'\n## {title}\n')
            lines += [f'- {rel}:{ln} {k}\n' for k, ln in sorted(rec[key].items())]
    if importers:
        lines.append('\n## Imported by\n')
        lines += [f'- {i}\n' for i in importers[:40]] + [more(40, len(importers), 'the import graph')]
    return ''.join(lines), call


def entry_points(rels, model):
    routes, cli, sched = [], [], []
    for rel in rels:
        rec = model['files'][rel]
        if rec['test']:
            continue
        routes += [(r['path'], r['method'], f'{rel}:{r["line"]}', r['handler']) for r in rec['routes']]
        sched += [f'{rel}:{s["line"]} {s["name"]}' for s in rec['schedulers']]
        if rec['cli']:
            cli.append(rel)
    return sorted(routes), sorted(cli), sorted(sched)


def card_text(domain, rels, model, sha, date, open_issues, chapters):
    rc, rd, sc, sd = domain
    call = _lib.call_number(rc, sc, AUTHOR, 'card', date)
    src = [r for r in rels if not model['files'][r]['test']]
    out = [header(f'{rd} / {sd}', sha, call), f'files: {len(src)} source, {len(rels) - len(src)} test; lines: {sum(model["files"][r]["lines"] for r in src)}\n\n']
    routes, cli, sched = entry_points(rels, model)
    out.append('## Entry points\n')
    out += [f'- {m} {p} -> {loc} {h}\n' for p, m, loc, h in routes[:CAP['routes']]] + [more(CAP['routes'], len(routes), 'catalog/routes.md')]
    out += [f'- CLI {r}\n' for r in cli[:CAP['sched']]] + [f'- scheduler {s}\n' for s in sched[:CAP['sched']]]
    if not (routes or cli or sched):
        out.append('- none detected\n')
    out.append('\n## Concepts defined here\n')
    defs = sorted(((d['kind'] != 'class', d['kind'] != 'constant', r, d['line'], d['name'], d['kind'])
                   for r in src for d in model['files'][r]['defs']))
    out += [f'- {r}:{ln} {n} ({k})\n' for _, _, r, ln, n, k in defs[:CAP['concepts']]] + [more(CAP['concepts'], len(defs), 'the chapters')]
    keys = sorted({(k, r, ln) for r in src for key in ('keys', 'tables') for k, ln in model['files'][r][key].items()})
    if keys:
        out.append('\n## Redis keys and tables\n')
        out += [f'- {r}:{ln} {k}\n' for k, r, ln in keys[:CAP['keys']]] + [more(CAP['keys'], len(keys), 'catalog/keys.md')]
    out.append('\n## Tests importing this domain\n')
    mine = set(src)
    tests = sorted(t for t, rec in model['files'].items() if rec['test'] and mine.intersection(model['imports'][t]))
    out += [f'- {t}\n' for t in tests[:CAP['tests']]] + [more(CAP['tests'], len(tests), 'the import graph')]
    if not tests:
        out.append('- none found\n')
    cited = sorted({(n, r, ln) for r in rels for n, ln in model['files'][r]['issues'].items() if open_issues is None or n in open_issues})
    out.append('\n## Issues cited in comments' + (' (open only)' if open_issues is not None else ' (state not checked)') + '\n')
    nums = sorted({n for n, _, _ in cited})
    out += [f'- #{n}: ' + ', '.join(f'{r}:{ln}' for m, r, ln in cited if m == n)[:200] + '\n' for n in nums[:CAP['issues']]]
    out += [more(CAP['issues'], len(nums), 'catalog/issues.md')]
    if not nums:
        out.append('- none\n')
    out.append('\n## Chapters\n' + ''.join(f'- {c}\n' for c in chapters))
    return ''.join(out), call


def catalogues(model, places, sha, date):
    concepts, routes, env, keys, issues = (collections.defaultdict(list) for _ in range(5))
    for rel, rec in model['files'].items():
        if rec['test']:
            for n, ln in rec['issues'].items():
                issues[n].append(f'{rel}:{ln}')
            continue
        rc, _, sc, _ = places[rel]
        call = _lib.call_number(rc, sc, AUTHOR, _graph.slug_module(rel), date)
        for d in rec['defs']:
            concepts[d['name']].append(f'{d["kind"]} | {rel}:{d["line"]} | {call}')
        for r in rec['routes']:
            routes[f'{r["path"]} {r["method"]}'].append(f'{r["handler"]} | {rel}:{r["line"]} | {rc}.{sc}')
        for k, ln in rec['env'].items():
            env[k].append(f'{rel}:{ln}')
        for key in ('keys', 'tables'):
            for k, ln in rec[key].items():
                keys[k].append(f'{rel}:{ln}')
        for n, ln in rec['issues'].items():
            issues[n].append(f'{rel}:{ln}')
    return concepts, routes, env, keys, issues


def flat(title, sha, table, fmt=str):
    body = ''.join(f'{fmt(k)} | {v}\n' for k in sorted(table, key=lambda x: (str(x).lower(), str(x))) for v in table[k])
    return f'{MARK}\n# {title}\n\ncommit: {sha}\n\n{body}'


def write_all(repo, out, files):
    """files: {abs path: text}. Writes through memory-library's write_text and prunes stale generated files per directory."""
    _graph.guard_paths(repo, files)
    by_dir = collections.defaultdict(set)
    for p, text in sorted(files.items()):
        _lib.write_text(out, p, text)
        by_dir[os.path.dirname(p)].add(p)
    for d, keep in sorted(by_dir.items()):
        _lib.prune_generated(out, d, keep, marker=MARK)


def build(repo, out, sha, date, cfg_path=None, issues_path=None):
    cls = _graph.Classifier(_graph.load_config(cfg_path))
    _graph.check_out_outside(repo, out)
    model = _graph.build_model(repo, cls)
    open_issues = load_open_issues(issues_path)
    lib = os.path.join(out, 'library')
    places = {rel: cls.place(rel) for rel in model['files']}
    files, index = {}, []
    for domain, rels in domains(model, cls).items():
        rc, rd, sc, sd = domain
        chapters = []
        for rel in rels:
            rec = model['files'][rel]
            if rec['test'] or not (rec['defs'] or rec['routes']):
                continue
            text, call = chapter_text(rel, rec, domain, sha, date, model['importers'].get(rel, []))
            name = _graph.slug_module(rel) + '.md'
            files[os.path.join(lib, rd, sd, 'chapters', name)] = text
            chapters.append(f'chapters/{name} ({call})')
        text, call = card_text(domain, rels, model, sha, date, open_issues, chapters)
        files[os.path.join(lib, rd, sd, 'CARD.md')] = text
        index.append(f'- {rd}/{sd}/CARD.md ({len(rels)} files) {call}\n')
    cats = catalogues(model, places, sha, date)
    letters = collections.defaultdict(dict)
    for name, v in cats[0].items():
        ch = name[0].lower() if name[:1].isalnum() else '_'
        letters[ch][name] = v
    for ch, table in letters.items():
        files[os.path.join(lib, 'catalog', 'concepts', f'{ch}.md')] = flat(f'Concepts starting {ch}', sha, table)
    for fname, title, table, fmt in (('routes', 'Routes', cats[1], str), ('env', 'Environment variables', cats[2], str),
                                     ('keys', 'Redis keys and tables', cats[3], str), ('issues', 'Issues cited', cats[4], lambda n: f'#{n}')):
        files[os.path.join(lib, 'catalog', f'{fname}.md')] = flat(title, sha, table, fmt)
    stats = {'files': len(model['files']), 'domains': len(index), 'concepts': len(cats[0]), 'routes': len(cats[1]),
             'env': len(cats[2]), 'keys': len(cats[3]), 'issues': len(cats[4]),
             'skipped': sum(1 for r in model['files'].values() if r.get('skipped'))}
    files[os.path.join(lib, 'INDEX.md')] = (f'{MARK}\n# Code map\n\ncommit: {sha}\ndate: {date}\n\n'
                                           + ''.join(f'- {k}: {v}\n' for k, v in stats.items()) + '\n## Cards\n' + ''.join(index)
                                           + ''.join(f'\nskipped: {r} ({rec["skipped"]})' for r, rec in sorted(model['files'].items()) if rec.get('skipped')))
    write_all(repo, out, files)
    return stats


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('repo')
    ap.add_argument('out')
    ap.add_argument('--commit')
    ap.add_argument('--commit-date')
    ap.add_argument('--config')
    ap.add_argument('--issues')
    a = ap.parse_args(argv)
    repo, out = os.path.abspath(a.repo), os.path.abspath(a.out)
    if not os.path.isdir(repo):
        _lib.die(f'not a directory: {repo}')
    sha, date = _graph.git_head(repo, a.commit or 'HEAD')
    sha, date = a.commit or sha, a.commit_date or date
    stats = build(repo, out, sha, date, a.config, a.issues)
    print(f'code map for {sha}: ' + ', '.join(f'{k}={v}' for k, v in stats.items()))


if __name__ == '__main__':
    main()
