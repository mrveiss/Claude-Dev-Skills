"""Static parsing for code-library (stdlib only; never imports or runs the target repo).

Python is read with ast.parse() on file TEXT; TS/JS/Vue with regexes over the text.
Nothing here imports a target module, executes a target file or touches sys.path.
"""
import ast
import hashlib
import io
import os
import re
import tokenize

PY_EXT = ('.py',)
FE_EXT = ('.ts', '.tsx', '.js', '.jsx', '.vue', '.mjs')
SKIP_DIRS = {'.git', 'node_modules', '__pycache__', '.venv', 'venv', 'dist', 'build', '.mypy_cache', '.pytest_cache', '.tox'}
MAX_BYTES = 1_000_000
ISSUE_RE = re.compile(r'#(\d{3,5})\b')
ROUTE_VERBS = {'get', 'post', 'put', 'delete', 'patch', 'head', 'options', 'websocket', 'api_route'}
ENV_CALLS = {'os.environ.get', 'os.getenv', 'environ.get', 'getenv', 'os.environ.setdefault', 'os.environ.pop'}
ENV_SUBS = {'os.environ', 'environ'}
KEY_RE = re.compile(r'^[a-z][a-z0-9_-]*(?::[A-Za-z0-9_{}*.-]+)+$')
URL_SCHEMES = {'http', 'https', 'redis', 'rediss', 'ws', 'wss', 'postgresql', 'postgres', 'sqlite', 'file', 'ftp', 'mailto', 'data', 'unix'}
TABLE_RE = re.compile(r'CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?[`"\[]?(\w+)', re.I)
CONST_RE = re.compile(r'^[A-Z][A-Z0-9_]+$')
DEFAULT_SCHED_DECORATOR = r'schedul|cron|periodic|interval|every'
DEFAULT_SCHED_NAME = r'^(run_)?(scheduled|periodic|cron)_|_scheduler$|_cron$'
TS_EXPORT = re.compile(r'^\s*export\s+(?:default\s+)?(?:declare\s+)?(?:async\s+)?(function|class|const|let|var|interface|type|enum)\s+(\w+)', re.M)
TS_EXPORT_LIST = re.compile(r'^\s*export\s*\{([^}]*)\}', re.M)
TS_IMPORT = re.compile(r'''(?:import\s+(?:[^'";]*?\s+from\s+)?|require\(\s*|export\s+[^'";]*?\s+from\s+)['"]([^'"]+)['"]''')
TS_ENV = re.compile(r'(?:import\.meta\.env|process\.env)\.(\w+)')
TS_COMMENT_ISSUE = re.compile(r'(?://|/\*|^\s*\*|<!--).*?#(\d{3,5})\b')


def is_test_path(rel):
    base = os.path.basename(rel)
    parts = rel.split('/')
    return (base.startswith('test_') or base.endswith(('_test.py', '.test.ts', '.spec.ts', '.test.js', '.spec.js'))
            or base == 'conftest.py' or any(p in ('tests', 'test', '__tests__') for p in parts[:-1]))


def walk(repo):
    """Sorted repo-relative posix paths of parseable source files."""
    out = []
    for base, dirs, files in os.walk(repo):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS)
        for f in sorted(files):
            if f.endswith(PY_EXT + FE_EXT):
                p = os.path.join(base, f)
                if os.path.isfile(p) and not os.path.islink(p) and os.path.getsize(p) <= MAX_BYTES:
                    out.append(os.path.relpath(p, repo).replace(os.sep, '/'))
    return out


def read(repo, rel):
    with open(os.path.join(repo, rel), encoding='utf-8', errors='replace') as fh:
        return fh.read()


def _sig(node, out):
    """Append a normalised token stream: names and literals erased, structure kept. Returns the node count."""
    n = 1
    out.append(type(node).__name__)
    body = getattr(node, 'body', None)
    skip_doc = isinstance(body, list) and body and isinstance(body[0], ast.Expr) \
        and isinstance(getattr(body[0], 'value', None), ast.Constant) and isinstance(body[0].value.value, str)
    for field, val in ast.iter_fields(node):
        if field in ('name', 'id', 'arg', 'ctx', 'type_comment', 'returns', 'annotation', 'decorator_list', 'kind'):
            continue
        if isinstance(val, ast.AST):
            n += _sig(val, out)
        elif isinstance(val, list):
            for i, item in enumerate(val):
                if field == 'body' and i == 0 and skip_doc:
                    continue
                if isinstance(item, ast.AST):
                    n += _sig(item, out)
        elif field != 'value' or not isinstance(node, ast.Constant):
            out.append(repr(val))
    return n


def normalised_hash(node):
    out = []
    count = _sig(node, out)
    return hashlib.sha1(' '.join(out).encode()).hexdigest(), count


def exact_hash(node):
    return hashlib.sha1(ast.dump(node).encode()).hexdigest()


def _defs(tree):
    defs, methods = [], []
    for node in tree.body:
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            kind = 'class' if isinstance(node, ast.ClassDef) else 'function'
            defs.append({'name': node.name, 'kind': kind, 'line': node.lineno, 'hash': exact_hash(node),
                         'end': getattr(node, 'end_lineno', node.lineno)})
            if kind == 'function':
                methods.append(_fn_record(node, node.name))
            else:
                methods += [_fn_record(m, f'{node.name}.{m.name}') for m in node.body
                            if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef))]
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for t in targets:
                if isinstance(t, ast.Name) and CONST_RE.match(t.id) and node.value is not None:
                    val = ast.unparse(node.value)
                    defs.append({'name': t.id, 'kind': 'constant', 'line': node.lineno, 'value': val[:200],
                                 'hash': hashlib.sha1(val.encode()).hexdigest()})
    return defs, methods


def _fn_record(node, qual):
    h, count = normalised_hash(node)
    return {'name': qual, 'line': node.lineno, 'norm': h, 'nodes': count}


def _prefixes(tree):
    pre = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call) \
                and _dotted(node.value.func).endswith('Router'):
            for kw in node.value.keywords:
                if kw.arg == 'prefix' and isinstance(kw.value, ast.Constant):
                    for t in node.targets:
                        if isinstance(t, ast.Name):
                            pre[t.id] = str(kw.value.value)
    return pre


def _dotted(node):
    """'a.b.c' for a Name/Attribute chain, else ''. Cheaper than ast.unparse on every node."""
    parts = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name):
        parts.append(node.id)
        return '.'.join(reversed(parts))
    return ''


def _route_of(node, pre):
    out = []
    for dec in node.decorator_list:
        if not (isinstance(dec, ast.Call) and isinstance(dec.func, ast.Attribute) and dec.func.attr in ROUTE_VERBS):
            continue
        arg = dec.args[0] if dec.args else next((k.value for k in dec.keywords if k.arg == 'path'), None)
        if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
            out.append({'method': dec.func.attr.upper(), 'path': pre.get(_dotted(dec.func.value), '') + arg.value,
                        'handler': node.name, 'line': node.lineno})
    return out


def _walk_facts(tree):
    """One pass over the tree: routes, imports, env vars, key and table literals."""
    pre = _prefixes(tree)
    routes, imports, env, keys, tables = [], [], {}, {}, {}
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            routes += _route_of(node, pre)
        elif isinstance(node, ast.Import):
            imports += [{'module': a.name, 'name': None, 'level': 0} for a in node.names]
        elif isinstance(node, ast.ImportFrom):
            imports += [{'module': node.module or '', 'name': a.name, 'level': node.level} for a in node.names]
        elif isinstance(node, ast.Call) and node.args and _dotted(node.func) in ENV_CALLS:
            _put_env(env, node.args[0], node.lineno)
        elif isinstance(node, ast.Subscript) and _dotted(node.value) in ENV_SUBS:
            _put_env(env, node.slice, node.lineno)
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            _put_literal(node, keys, tables)
    routes.sort(key=lambda r: (r['path'], r['method'], r['line']))
    return routes, imports, env, keys, tables


def _put_env(env, arg, line):
    if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
        env.setdefault(arg.value, line)


def _put_literal(node, keys, tables):
    s = node.value
    if len(s) <= 80 and KEY_RE.match(s) and '.' not in s.split(':')[0] and s.split(':')[0] not in URL_SCHEMES:
        keys.setdefault(s, node.lineno)
    elif 'CREATE' in s.upper() and len(s) < 20000:
        m = TABLE_RE.search(s)
        if m:
            tables.setdefault(m.group(1), node.lineno)


def _issues_py(text):
    out = {}
    if not ISSUE_RE.search(text):
        return out  # tokenizing is the costly part; only files that cite a number need it
    try:
        for tok in tokenize.generate_tokens(io.StringIO(text).readline):
            if tok.type == tokenize.COMMENT:
                for m in ISSUE_RE.finditer(tok.string):
                    out.setdefault(int(m.group(1)), tok.start[0])
    except (tokenize.TokenError, IndentationError, SyntaxError):
        pass
    return out


def _is_main_guard(node):
    return isinstance(node, ast.If) and isinstance(node.test, ast.Compare) and isinstance(node.test.left, ast.Name) \
        and node.test.left.id == '__name__' and any(isinstance(c, ast.Constant) and c.value == '__main__' for c in node.test.comparators)


def _schedulers(tree, dec_re, name_re):
    out = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            decs = [ast.unparse(d) for d in node.decorator_list]
            if any(re.search(dec_re, d, re.I) for d in decs) or re.search(name_re, node.name):
                out.append({'name': node.name, 'line': node.lineno})
    return out


def parse_python(text, sched_dec=DEFAULT_SCHED_DECORATOR, sched_name=DEFAULT_SCHED_NAME):
    try:
        tree = ast.parse(text)
    except (SyntaxError, ValueError, RecursionError):
        return {'lang': 'py', 'error': True, 'defs': [], 'methods': [], 'routes': [], 'imports': [], 'env': {},
                'keys': {}, 'tables': {}, 'issues': _issues_py(text), 'cli': False, 'schedulers': []}
    defs, methods = _defs(tree)
    routes, imports, env, keys, tables = _walk_facts(tree)
    return {'lang': 'py', 'error': False, 'defs': defs, 'methods': methods, 'routes': routes,
            'imports': imports, 'env': env, 'keys': keys, 'tables': tables, 'issues': _issues_py(text),
            'cli': any(_is_main_guard(n) for n in tree.body), 'schedulers': _schedulers(tree, sched_dec, sched_name)}


def parse_frontend(text):
    defs = []
    for m in TS_EXPORT.finditer(text):
        kind = {'function': 'function', 'class': 'class', 'interface': 'type', 'type': 'type', 'enum': 'type'}.get(m.group(1), 'constant')
        defs.append({'name': m.group(2), 'kind': kind, 'line': text.count('\n', 0, m.start()) + 1,
                     'hash': hashlib.sha1(m.group(0).encode()).hexdigest()})
    for m in TS_EXPORT_LIST.finditer(text):
        for part in m.group(1).split(','):
            name = part.strip().split(' as ')[-1].strip()
            if name.isidentifier():
                defs.append({'name': name, 'kind': 'export', 'line': text.count('\n', 0, m.start()) + 1,
                             'hash': hashlib.sha1(name.encode()).hexdigest()})
    env = {}
    for m in TS_ENV.finditer(text):
        env.setdefault(m.group(1), text.count('\n', 0, m.start()) + 1)
    issues = {}
    for i, line in enumerate(text.splitlines(), 1):
        m = TS_COMMENT_ISSUE.search(line)
        if m:
            issues.setdefault(int(m.group(1)), i)
    return {'lang': 'fe', 'error': False, 'defs': defs, 'methods': [], 'routes': [], 'env': env, 'keys': {}, 'tables': {},
            'imports': [{'module': m, 'name': None, 'level': 0} for m in TS_IMPORT.findall(text)],
            'issues': issues, 'cli': False, 'schedulers': []}


def parse_file(repo, rel, sched_dec=DEFAULT_SCHED_DECORATOR, sched_name=DEFAULT_SCHED_NAME):
    text = read(repo, rel)
    rec = parse_python(text, sched_dec, sched_name) if rel.endswith(PY_EXT) else parse_frontend(text)
    rec['lines'] = text.count('\n') + 1
    rec['sha'] = hashlib.sha1(text.encode('utf-8', 'replace')).hexdigest()
    return rec
