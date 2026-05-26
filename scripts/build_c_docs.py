#!/usr/bin/env python3
"""Extract C API documentation from `brs_ide/elm11/c/build/*.h`.

Run after editing the bundled headers:

    python3 scripts/build_c_docs.py

Output is written to `brs_ide/docs_c_data.json` and consumed by the
runtime DocsPanel when the active workspace is in C mode.
"""
import json
import re
import sys
from pathlib import Path

ROOT        = Path(__file__).resolve().parent.parent
HEADERS_DIR = ROOT / 'brs_ide' / 'elm11' / 'c' / 'build'
DESCRS      = ROOT / 'brs_ide' / 'elm11' / 'c' / 'build' / 'c_descriptions.json'
OUT         = ROOT / 'brs_ide' / 'docs_c_data.json'


# Strip block + line comments before structural parsing.
_COMMENT_RE = re.compile(r'/\*.*?\*/|//[^\n]*', re.DOTALL)

# Function declaration. Tolerant of:
#   <const|volatile|static>* <type> <*>* <name> ( <args> ) [trailing-attribs];
_FN_RE = re.compile(
    r'^(?P<rt>(?:(?:const|volatile|static|inline|extern)\s+)*'
    r'[\w*]+(?:\s*\*+)?)\s+(?P<name>\w+)\s*\((?P<args>[^)]*)\)'
    r'(?P<attribs>(?:\s+\w+)*)\s*;',
    re.MULTILINE,
)

# Macro definition (function-like or value). The `rest` group is parsed
# out into args/value below depending on whether `(` follows the name.
_MACRO_RE = re.compile(
    r'^\s*#define\s+(?P<name>\w+)(?P<rest>[^\n]*)$', re.MULTILINE,
)

# Filter out things that look like a function declaration but aren't:
# control-flow keywords, sizeof, the `enum`/`struct` keywords, etc.
_NON_FN_NAMES = {
    'if', 'while', 'for', 'switch', 'return', 'sizeof',
    'typedef', 'enum', 'struct', 'union',
}


def _normspace(s: str) -> str:
    return re.sub(r'\s+', ' ', s).strip()


def _split_args(args: str) -> str:
    return _normspace(args)


def _parse_macro_rest(rest: str) -> tuple[str, str]:
    """Return (args_with_parens, value) split for function-like macros."""
    rest = rest.rstrip()
    if rest.startswith('('):
        depth = 0
        end = 0
        for i, c in enumerate(rest):
            if c == '(':
                depth += 1
            elif c == ')':
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break
        return rest[:end], rest[end:].strip()
    return '', rest.strip()


def extract_header(path: Path) -> dict:
    text = _COMMENT_RE.sub('', path.read_text(encoding='utf-8'))
    functions: list[dict] = []
    for m in _FN_RE.finditer(text):
        name = m.group('name')
        if name in _NON_FN_NAMES:
            continue
        rt   = _normspace(m.group('rt'))
        args = _split_args(m.group('args'))
        attribs = _normspace(m.group('attribs'))
        sig = f'{rt} {name}({args})'
        if attribs:
            sig = f'{sig} {attribs}'
        functions.append({
            'name':        name,
            'signature':   sig,
            'header':      path.name,
            'description': '',
        })

    macros: list[dict] = []
    for m in _MACRO_RE.finditer(text):
        name = m.group('name')
        args, value = _parse_macro_rest(m.group('rest'))
        macros.append({
            'name':        name,
            'args':        args,
            'value':       value,
            'header':      path.name,
            'description': '',
        })
    return {'functions': functions, 'macros': macros}


def _load_descriptions() -> dict:
    """Sidecar file `c_descriptions.json` keyed by `{functions: {name: text},
    macros: {name: text}}`. Optional — missing file is non-fatal."""
    if not DESCRS.is_file():
        return {'functions': {}, 'macros': {}}
    raw = json.loads(DESCRS.read_text(encoding='utf-8'))
    return {
        'functions': raw.get('functions', {}) or {},
        'macros':    raw.get('macros',    {}) or {},
    }


def main():
    if not HEADERS_DIR.is_dir():
        print(f'No header directory at {HEADERS_DIR}', file=sys.stderr)
        sys.exit(1)
    descs = _load_descriptions()
    used_fn:    set[str] = set()
    used_macro: set[str] = set()
    headers = []
    for h in sorted(HEADERS_DIR.glob('*.h')):
        info = extract_header(h)
        for fn in info['functions']:
            if fn['name'] in descs['functions']:
                fn['description'] = descs['functions'][fn['name']]
                used_fn.add(fn['name'])
        for mc in info['macros']:
            if mc['name'] in descs['macros']:
                mc['description'] = descs['macros'][mc['name']]
                used_macro.add(mc['name'])
        headers.append({
            'name':      h.name,
            'functions': info['functions'],
            'macros':    info['macros'],
        })
    data = {'headers': headers}
    OUT.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    fns    = sum(len(h['functions']) for h in headers)
    macros = sum(len(h['macros'])    for h in headers)
    documented_fn = sum(
        1 for h in headers for f in h['functions'] if f['description'])
    documented_mc = sum(
        1 for h in headers for m in h['macros']    if m['description'])
    print(f'Wrote {OUT}: {len(headers)} headers, {fns} functions '
          f'({documented_fn} documented), {macros} macros '
          f'({documented_mc} documented)')
    # Warn about descriptions in the sidecar that no header provided.
    stale_fn = set(descs['functions']) - used_fn
    stale_mc = set(descs['macros'])    - used_macro
    if stale_fn:
        print(f'  warn: {len(stale_fn)} unused function description(s): '
              f'{sorted(stale_fn)[:5]}', file=sys.stderr)
    if stale_mc:
        print(f'  warn: {len(stale_mc)} unused macro description(s): '
              f'{sorted(stale_mc)[:5]}', file=sys.stderr)


if __name__ == '__main__':
    main()
