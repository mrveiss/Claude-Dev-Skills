#!/usr/bin/env python3
"""Shelve one flat topic list into a library shelf.

usage: python3 -I build.py <memory-dir> <shelf>      (shelf = code or name from classes.json)
       python3 -I build.py <memory-dir> --fact <file>  (one new fact: incremental, see below)

--fact finds the shelf whose source lists the fact, rewrites only that fact's chapter and
the shelf card, then re-renders only the catalogue groups listing it (catalog.py --fact).
The result is byte-identical to a full build + catalog run. After editing classes.json run
the full build instead.

Reads <memory-dir>/library/classes.json and the shelf's source topic file; writes chapters
and CARD.md under <memory-dir>/library/. Idempotent; never touches a fact file.
"""
import collections
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _lib  # noqa: E402


def entries(mem, shelf):
    src = os.path.join(mem, shelf['source'])
    if not os.path.isfile(src):
        _lib.die(f'missing source topic list {src}')
    with open(src, encoding='utf-8') as fh:
        return [ln.rstrip('\n') for ln in fh if ln.startswith('- [')]


def fact_name(line):
    m = _lib.LINK_RE.search(line)
    return os.path.basename(m.group(1)) if m else None


def pick_author(mem, shelf, line, fact):
    """Frontmatter author wins; else the first author whose match rules hit; else default."""
    if fact:
        fm = _lib.frontmatter(os.path.join(mem, fact)).get('author')
        if fm:
            return _lib.slug(fm)
    for name, spec in shelf.get('authors', {}).items():
        m = spec.get('match', {})
        if (m.get('file') and fact and re.search(m['file'], fact)) or \
           (m.get('line') and re.search(m['line'], line)):
            return name
    return shelf.get('default_author', 'unknown')


def pick_chapter(shelf, line):
    for ch in shelf['chapters']:
        if re.search(ch['regex'], line):
            return ch
    return shelf['other']


def classify(mem, shelf):
    books = collections.defaultdict(lambda: collections.defaultdict(list))
    missing = []
    for line in entries(mem, shelf):
        fact = fact_name(line)
        if fact and not os.path.exists(os.path.join(mem, fact)):
            missing.append(fact)
        ch = pick_chapter(shelf, line)
        books[pick_author(mem, shelf, line, fact)][ch['key']].append(line)
    return books, missing


def chapter_meta(shelf):
    meta = {c['key']: c for c in shelf['chapters']}
    meta[shelf['other']['key']] = shelf['other']
    return meta


def author_label(shelf, author):
    return shelf.get('authors', {}).get(author, {}).get('label', author)


def write_chapter(mem, cfg, shelf_code, shelf, author, ch, items):
    room = ch.get('room') or shelf['room']
    d = os.path.join(mem, 'library', _lib.room_dir(cfg, room), shelf['name'], author)
    body = [_lib.GENERATED, f'# {ch["title"]}', '',
            f'Shelf: {shelf["title"]} · Book: {author_label(shelf, author)} · '
            f'{len(items)} entries · call prefix `{room}.{shelf_code}/{author}/{ch["code"]}`', '',
            ch['purpose'] + '.', '']
    body += [_lib.relink(ln, mem, d) for ln in items]
    path = os.path.join(d, ch['key'] + '.md')
    _lib.write_text(mem, path, '\n'.join(body) + '\n')
    return path


def ordered(shelf, books):
    known = [a for a in shelf.get('authors', {}) if a in books]
    return known + sorted(a for a in books if a not in known)


def card_rows(cfg, shelf_code, shelf, books, meta, author):
    rows = ['| Chapter | Call prefix | Purpose | Entries |', '|---|---|---|---|']
    for key in sorted(books[author], key=list(meta).index):
        items = books[author][key]
        ch = meta[key]
        room = ch.get('room') or shelf['room']
        if room != shelf['room']:
            continue
        rows.append(f'| [{ch["title"]}]({author}/{key}.md) | `{room}.{shelf_code}/{author}/{ch["code"]}` '
                    f'| {ch["purpose"]} | {len(items)} |')
    return rows


def write_card(mem, cfg, shelf_code, shelf, books, meta):
    card = [_lib.GENERATED, f'# Shelf card: {shelf["title"]}', '',
            'Read this card, then open ONE chapter. Books are ordered by authority as listed; '
            'within a book, the newer dated rule wins.', '']
    for author in ordered(shelf, books):
        rows = card_rows(cfg, shelf_code, shelf, books, meta, author)
        if len(rows) > 2:
            card += [f'## {author_label(shelf, author)}', ''] + rows + ['']
    card += ['## Elsewhere in the library', '']
    for room, label in elsewhere(shelf, books, meta).items():
        card.append(f'- `library/{_lib.room_dir(cfg, room)}/{shelf["name"]}/`: {label}')
    path = os.path.join(mem, 'library', _lib.room_dir(cfg, shelf['room']), shelf['name'], 'CARD.md')
    _lib.write_text(mem, path, '\n'.join(card) + '\n')
    return path


def elsewhere(shelf, books, meta):
    counts = collections.Counter()
    for chs in books.values():
        for key, items in chs.items():
            room = meta[key].get('room') or shelf['room']
            if room != shelf['room']:
                counts[room] += len(items)
    return {room: f'{n} entries moved out of the shelf room' for room, n in counts.items()}


def shelf_of_fact(mem, cfg, fact):
    for code, shelf in cfg['shelves'].items():
        src = os.path.join(mem, shelf['source'])
        if os.path.isfile(src) and any(fact_name(ln) == fact for ln in entries(mem, shelf)):
            return code, shelf
    _lib.die(f'{fact} is not linked from any shelf source in classes.json')


def build_fact(mem, cfg, fact):
    code, shelf = shelf_of_fact(mem, cfg, fact)
    books, _ = classify(mem, shelf)
    meta = chapter_meta(shelf)
    for author, chs in books.items():
        for key, items in chs.items():
            if any(fact_name(ln) == fact for ln in items):
                write_chapter(mem, cfg, code, shelf, author, meta[key], items)
    write_card(mem, cfg, code, shelf, books, meta)
    print(f'shelf {code}: rebuilt the chapter of {fact} and the card')


def main(argv):
    if len(argv) == 4 and argv[2] == '--fact':
        mem = os.path.abspath(argv[1])
        cfg = _lib.load_classes(mem)
        build_fact(mem, cfg, os.path.basename(argv[3]))
        import catalog
        catalog.regenerate(mem, cfg, os.path.basename(argv[3]))
        return
    if len(argv) != 3:
        _lib.die(__doc__)
    mem, ref = os.path.abspath(argv[1]), argv[2]
    cfg = _lib.load_classes(mem)
    code, shelf = _lib.find_shelf(cfg, ref)
    books, missing = classify(mem, shelf)
    meta = chapter_meta(shelf)
    written = set()
    for author, chs in books.items():
        for key, items in chs.items():
            written.add(write_chapter(mem, cfg, code, shelf, author, meta[key], items))
    written.add(write_card(mem, cfg, code, shelf, books, meta))
    for room in cfg['rooms']:
        base = os.path.join(mem, 'library', _lib.room_dir(cfg, room), shelf['name'])
        for author in os.listdir(base) if os.path.isdir(base) else []:
            _lib.prune_generated(mem, os.path.join(base, author), written)
    total = sum(len(i) for c in books.values() for i in c.values())
    print(f'shelf {code}: {total} entries, {len(missing)} missing targets {missing[:5]}')
    for author, chs in books.items():
        print(' ', author, {k: len(v) for k, v in sorted(chs.items())})


if __name__ == '__main__':
    main(sys.argv)
