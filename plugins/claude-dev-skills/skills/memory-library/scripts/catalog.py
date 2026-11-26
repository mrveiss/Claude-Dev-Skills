#!/usr/bin/env python3
"""Regenerate the lookup catalogues under <memory-dir>/library/catalog/.

usage: python3 -I catalog.py <memory-dir>

Catalogues: by topic, author, date created, title A-Z, kind, issue/PR. Every line carries
its call number (room.shelf/author/chapter/date). Idempotent; never touches a fact file.
"""
import collections
import datetime
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _lib  # noqa: E402

Row = collections.namedtuple(
    'Row', 'room shelf author chapter ctitle cpath line title fact date src')


def code_maps(cfg):
    rooms = {v['dir']: k for k, v in cfg['rooms'].items()}
    shelves = {v['name']: k for k, v in cfg['shelves'].items()}
    return rooms, shelves


def chapter_code(shelf_cfg, key):
    for ch in shelf_cfg['chapters'] + [shelf_cfg['other']]:
        if ch['key'] == key:
            return ch['code']
    return key[:3].upper()


def entry_date(mem, line, fact):
    """(date, src): src is created (frontmatter), text (in the entry) or file (approximate)."""
    fm = _lib.frontmatter(os.path.join(mem, fact)) if fact else {}
    for text, src in ((fm.get('created', ''), 'created'), (line, 'text')):
        d = _lib.DATE_RE.search(text)
        if d:
            return '-'.join(d.groups()), src
    try:
        st = os.stat(os.path.join(mem, fact))
    except (OSError, TypeError):
        return 'unknown', 'none'
    stamp = getattr(st, 'st_birthtime', st.st_mtime)
    return datetime.date.fromtimestamp(stamp).isoformat(), 'file'


def collect(mem, cfg):
    rooms, shelves = code_maps(cfg)
    lib = os.path.join(mem, 'library')
    rows = []
    for rdir, rcode in sorted(rooms.items()):
        for sname, scode in sorted(shelves.items()):
            for author in sorted(_subdirs(os.path.join(lib, rdir, sname))):
                rows += chapter_rows(mem, cfg, rcode, scode, sname, rdir, author)
    return apply_bulk_rule(rows)


def _subdirs(path):
    return [n for n in os.listdir(path) if os.path.isdir(os.path.join(path, n))] \
        if os.path.isdir(path) else []


def chapter_rows(mem, cfg, rcode, scode, sname, rdir, author):
    d = os.path.join(mem, 'library', rdir, sname, author)
    shelf_cfg = cfg['shelves'][scode]
    out = []
    for name in sorted(os.listdir(d)):
        if not name.endswith('.md'):
            continue
        path = os.path.join(d, name)
        with open(path, encoding='utf-8') as fh:
            lines = fh.read().splitlines()
        title = next((ln.lstrip('# ') for ln in lines if ln.startswith('# ')), name)
        ccode = chapter_code(shelf_cfg, name[:-3])
        for ln in (x for x in lines if x.startswith('- [')):
            fact = os.path.basename(_lib.LINK_RE.search(ln).group(1)) if _lib.LINK_RE.search(ln) else None
            date, src = entry_date(mem, ln, fact)
            t = re.match(r'- \[([^\]]*)\]', ln)
            out.append(Row(rcode, scode, author, ccode, title, path, ln,
                           t.group(1) if t else ln, fact, date, src))
    return out


def apply_bulk_rule(rows):
    per_day = collections.Counter(r.date for r in rows if r.src == 'file')
    bulk = {d for d, n in per_day.items() if n >= _lib.BULK_THRESHOLD}
    return [r._replace(date='unknown', src='bulk') if r.src == 'file' and r.date in bulk else r
            for r in rows]


def call(r):
    return _lib.call_number(r.room, r.shelf, r.author, r.chapter, r.date, r.src == 'file')


def order(r):
    return _lib.sort_key(r.room, r.shelf, r.author, r.chapter, r.date)


def entry_line(mem, r, frm, prefix=''):
    return f'- `{call(r)}` · {prefix}' + _lib.relink(r.line, mem, frm)[2:]


def grouped(mem, cat, name, title, note, rows, keyf, label=lambda g: g, sortf=order):
    d = os.path.join(cat, name)
    groups = collections.defaultdict(list)
    for r in rows:
        for g in keyf(r):
            groups[g].append(r)
    idx = [_lib.GENERATED, f'# Catalogue: {title}', '', note, '', '| Group | Entries |', '|---|---|']
    keep = set()
    for g in sorted(groups, key=str):
        fn = re.sub(r'[^A-Za-z0-9_-]', '_', str(g)) + '.md'
        body = [_lib.GENERATED, f'# {title}: {label(g)}', '', f'{len(groups[g])} entries.', '']
        body += [entry_line(mem, r, d) for r in sorted(groups[g], key=sortf)]
        keep.add(os.path.join(d, fn))
        _lib.write_text(mem, os.path.join(d, fn), '\n'.join(body) + '\n')
        idx.append(f'| [{label(g)}]({name}/{fn}) | {len(groups[g])} |')
    _lib.prune_generated(mem, d, keep)
    _lib.write_text(mem, os.path.join(cat, name + '.md'), '\n'.join(idx) + '\n')


def kind(mem, r):
    fm = _lib.frontmatter(os.path.join(mem, r.fact)) if r.fact else {}
    if fm.get('type'):
        return [fm['type']]
    for k in ('feedback', 'gotcha', 'project', 'reference', 'user'):
        if (r.fact or '').startswith(k + '_'):
            return [k]
    return ['untyped']


def first_letter(r):
    c = r.title.lstrip('"\'`-*_ ')[:1].upper()
    return [c if c.isalpha() else '#']


def issue_groups(r):
    return sorted({f'{int(n) // 1000}xxx' for n in re.findall(r'#(\d{3,5})\b', r.line)})


def write_topic_author(mem, cfg, cat, rows):
    rooms = cfg['rooms']
    out = [_lib.GENERATED, '# Catalogue: by topic', '', '| Shelf | Card | Authors | Entries |', '|---|---|---|---|']
    for scode in sorted({r.shelf for r in rows}):
        rs = [r for r in rows if r.shelf == scode]
        sh = cfg['shelves'][scode]
        card = f'../{rooms[sh["room"]]["dir"]}/{sh["name"]}/CARD.md'
        out.append(f'| {scode} {sh["title"]} | [CARD]({card}) | {", ".join(sorted({r.author for r in rs}))} | {len(rs)} |')
    _lib.write_text(mem, os.path.join(cat, 'by-topic.md'), '\n'.join(out) + '\n')
    out = [_lib.GENERATED, '# Catalogue: by author', '', 'One book = one author on one shelf.', '']
    for a in sorted({r.author for r in rows}):
        out += [f'## {a}', '', '| Call prefix | Chapter | Entries |', '|---|---|---|']
        keys = sorted({(r.room, r.shelf, r.chapter, r.ctitle, r.cpath) for r in rows if r.author == a})
        for room, shelf, ch, title, path in keys:
            n = sum(1 for r in rows if r.author == a and r.cpath == path)
            rel = os.path.relpath(path, cat)
            out.append(f'| `{room}.{shelf}/{a}/{ch}` | [{title}]({rel}) | {n} |')
        out.append('')
    _lib.write_text(mem, os.path.join(cat, 'by-author.md'), '\n'.join(out))


def write_by_date(mem, cat, rows):
    note = ('Date = created: in the fact frontmatter, else a date written in the entry, else the '
            'fact file time, shown with a leading ~ (approximate: a copy or restore resets file '
            f'times). A day shared by {_lib.BULK_THRESHOLD} or more file-dated entries is a bulk '
            'copy; those entries are listed as unknown.')
    grouped(mem, cat, 'by-date', 'date created', note, rows,
            lambda r: [r.date[:7] if r.date != 'unknown' else 'unknown'],
            sortf=lambda r: (r.date, order(r)))


def main(argv):
    if len(argv) != 2:
        _lib.die(__doc__)
    mem = os.path.abspath(argv[1])
    cfg = _lib.load_classes(mem)
    rows = collect(mem, cfg)
    cat = os.path.join(mem, 'library', 'catalog')
    write_topic_author(mem, cfg, cat, rows)
    write_by_date(mem, cat, rows)
    grouped(mem, cat, 'by-title', 'title A-Z', 'Entry titles, one file per first letter.',
            rows, first_letter, sortf=lambda r: (r.title.lower(), order(r)))
    grouped(mem, cat, 'by-kind', 'kind', 'feedback, gotcha, project, reference or user (frontmatter type, else file prefix).',
            rows, lambda r: kind(mem, r))
    grouped(mem, cat, 'by-issue', 'issue or PR', 'Entries naming an issue or PR, grouped per thousand.',
            rows, issue_groups, label=lambda g: f'#{g}')
    print(f'rows {len(rows)}; dated from file {sum(r.src == "file" for r in rows)}; '
          f'unknown {sum(r.date == "unknown" for r in rows)}')


if __name__ == '__main__':
    main(sys.argv)
