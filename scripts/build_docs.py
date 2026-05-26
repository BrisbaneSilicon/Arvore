#!/usr/bin/env python3
"""Extract the embLua PDF documentation into structured JSON.

This is a build-time tool — run it whenever the PDF is updated.
    python3 scripts/build_docs.py [path/to/embLua_ProductDocumentation.pdf]

Requires `pdftotext` (from poppler-utils) on PATH.
"""
import json
import re
import subprocess
import sys
from pathlib import Path

HERE    = Path(__file__).resolve().parent
REPO    = HERE.parent
OUT     = REPO / 'brs_ide' / 'docs_data.json'
DEFAULT = REPO / 'embLua_ProductDocumentation.pdf'

# Page ranges derived from the PDF table of contents.
API_FIRST, API_LAST           = 32, 50   # section 5
USAGE_FIRST, USAGE_LAST       = 51, 73   # section 6
EXAMPLES_FIRST, EXAMPLES_LAST = 74, 97   # section 7

# ── pdftotext helpers ──────────────────────────────────────────────────────

def _extract(pdf: Path, first: int, last: int) -> list[str]:
    out = subprocess.check_output(
        ['pdftotext', '-layout', '-f', str(first), '-l', str(last),
         str(pdf), '-'], text=True)
    return out.splitlines()

_HEADER_FOOTER_RE = re.compile(
    r'^\s*(embLua – Documentation|[A-Z][A-Za-z /]+? – \d+)\s*$')

def _strip_chrome(lines: list[str]) -> list[str]:
    return [l for l in lines if not _HEADER_FOOTER_RE.match(l)]

# ── Structural parsing ─────────────────────────────────────────────────────

_SUBSEC_RE = re.compile(r'^\s*(\d+(?:\.\d+){1,3})\s+(.+?)\s*$')

def _split_subsections(lines: list[str]) -> list[tuple[str, str, list[str]]]:
    """Return list of (number, title, body_lines) for each `N.N(.N(.N))` heading."""
    sections: list[tuple[str, str, list[str]]] = []
    current: tuple[str, str, list[str]] | None = None
    for raw in lines:
        m = _SUBSEC_RE.match(raw)
        is_heading = (
            m is not None
            and raw.lstrip().startswith(m.group(1))
            and not raw.lstrip().startswith(m.group(1) + '.')
            # Filter out numeric-looking content lines (single digit chapters like "1")
            and len(m.group(1).split('.')) >= 2
        )
        if is_heading:
            if current:
                sections.append(current)
            current = (m.group(1), m.group(2).strip(), [])
        elif current:
            current[2].append(raw)
    if current:
        sections.append(current)
    return sections

# ── Table row extraction ───────────────────────────────────────────────────

_TABLE_HEADER_RE = re.compile(
    r'^(\s*)(Function|Constant|Variable)(\s+)(Description)\s*$')

_COL_GAP_RE = re.compile(r'\S(\s{3,})\S')

def _table_kind(body: list[str]) -> str | None:
    for line in body:
        m = _TABLE_HEADER_RE.match(line)
        if m:
            return m.group(2).lower()
    return None

def _row_blocks(body: list[str]) -> list[list[str]]:
    """Split body at blank lines, keep only non-empty blocks after the table header."""
    blocks: list[list[str]] = []
    buf: list[str] = []
    seen_header = False
    for line in body:
        if _TABLE_HEADER_RE.match(line):
            seen_header = True
            continue
        if not seen_header:
            continue
        if line.strip():
            buf.append(line)
        else:
            if buf:
                blocks.append(buf)
                buf = []
    if buf:
        blocks.append(buf)
    return blocks

def _detect_boundary(block: list[str]) -> int:
    """Return the column where the description text begins, detected from the block."""
    for line in block:
        m = _COL_GAP_RE.search(line)
        if m:
            return m.end(1)
    # Fallback: no clear gap — treat the whole line as a name
    return max((len(l) for l in block), default=0)

def _parse_row(block: list[str]) -> tuple[str, str]:
    """Return (name, description) for a single row block."""
    boundary = _detect_boundary(block)
    name_parts: list[str] = []
    desc_parts: list[str] = []
    for line in block:
        padded = line.ljust(boundary)
        left  = padded[:boundary].strip()
        right = padded[boundary:].rstrip()
        if left:
            name_parts.append(left)
        if right:
            desc_parts.append(right)
    name = re.sub(r'\s+', '', ''.join(name_parts))
    return name, '\n'.join(desc_parts).strip()

# ── API section ────────────────────────────────────────────────────────────

def _category_path(num: str, title: str,
                   top: dict[str, str]) -> tuple[str, str]:
    """Return (top_category, sub_category) from a section number like 5.2.1.8."""
    parts = num.split('.')
    # parts[0] = 5 (API), parts[1] = 1 (Constants) or 2 (Functions) or 3 (Variables)
    top_name = top.get(parts[1], 'Misc')
    return top_name, title

def _extract_api(pdf: Path) -> list[dict]:
    lines = _strip_chrome(_extract(pdf, API_FIRST, API_LAST))
    sections = _split_subsections(lines)
    # Top-level labels (5.1, 5.2, 5.3)
    top = {}
    for num, title, _ in sections:
        parts = num.split('.')
        if len(parts) == 2 and parts[0] == '5':
            top[parts[1]] = title

    entries: list[dict] = []
    # Track nested category when an intermediate heading exists (e.g. 5.2.1)
    intermediate = {}
    for num, title, _ in sections:
        parts = num.split('.')
        if len(parts) == 3 and parts[0] == '5':
            intermediate[f'{parts[1]}.{parts[2]}'] = title

    for num, title, body in sections:
        parts = num.split('.')
        kind = _table_kind(body)
        if kind is None:
            continue
        top_name = top.get(parts[1], 'Misc')
        if len(parts) == 2:
            category = title
        elif len(parts) == 4:
            mid_key = f'{parts[1]}.{parts[2]}'
            mid = intermediate.get(mid_key, '')
            category = ' › '.join(filter(None, [top_name, mid, title]))
        else:
            category = f'{top_name} › {title}'
        for block in _row_blocks(body):
            name, desc = _parse_row(block)
            if not name:
                continue
            entries.append({
                'name':        name,
                'kind':        kind,
                'category':    category,
                'description': desc,
            })
    return entries

# ── Example Programs section ───────────────────────────────────────────────

def _extract_examples(pdf: Path) -> list[dict]:
    lines = _strip_chrome(_extract(pdf, EXAMPLES_FIRST, EXAMPLES_LAST))
    sections = _split_subsections(lines)
    examples: list[dict] = []
    for num, title, body in sections:
        parts = num.split('.')
        if len(parts) != 2 or parts[0] != '7':
            continue
        # Strip leading blank lines and leading 1-space indent uniformly
        src_lines = body
        # Remove up to two leading blank lines
        while src_lines and not src_lines[0].strip():
            src_lines = src_lines[1:]
        # Determine common leading indent among non-blank lines
        non_blank = [l for l in src_lines if l.strip()]
        indent = min((len(l) - len(l.lstrip(' ')) for l in non_blank), default=0)
        if indent:
            src_lines = [l[indent:] if len(l) >= indent else l for l in src_lines]
        code = '\n'.join(src_lines).rstrip() + '\n'
        examples.append({
            'title': title,
            'code':  code,
        })
    return examples

# ── Example Usage section (prose walkthroughs) ────────────────────────────

def _extract_usage(pdf: Path) -> list[dict]:
    lines = _strip_chrome(_extract(pdf, USAGE_FIRST, USAGE_LAST))
    sections = _split_subsections(lines)
    usage: list[dict] = []
    for num, title, body in sections:
        parts = num.split('.')
        if len(parts) != 2 or parts[0] != '6':
            continue
        text_lines = [l.rstrip() for l in body]
        # Trim leading/trailing blank lines
        while text_lines and not text_lines[0].strip():
            text_lines.pop(0)
        while text_lines and not text_lines[-1].strip():
            text_lines.pop()
        usage.append({
            'title': title,
            'body':  '\n'.join(text_lines),
        })
    return usage

# ── Main ───────────────────────────────────────────────────────────────────

def main():
    pdf = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT
    if not pdf.is_file():
        print(f'PDF not found: {pdf}', file=sys.stderr)
        sys.exit(1)
    data = {
        'source':   pdf.name,
        'api':      _extract_api(pdf),
        'examples': _extract_examples(pdf),
        'usage':    _extract_usage(pdf),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    print(f'Wrote {OUT}  (api={len(data["api"])}  '
          f'examples={len(data["examples"])}  usage={len(data["usage"])})')


if __name__ == '__main__':
    main()
