#!/usr/bin/env python3
"""Generate ``summary.csv`` from the (empty) stub files in ``stubs/``.

Each stub's *filename* encodes one overlay configuration as underscore-separated
fields, in the same order as the CSV columns below, e.g.::

    115200_66000000_1_1_1_1_0_1_16_768_3072_3_12_255_0_0_3_65535_1

The file contents are ignored — only the name matters. The clock field is given
in Hz in the filename and emitted in MHz to match the ``Clk Mhz`` column.

Usage::

    python build_summary.py            # stubs/ -> summary.csv (alongside this file)
    python build_summary.py --check    # exit non-zero if summary.csv is stale
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# CSV columns, in the order the stub filename's fields appear.
COLUMNS = [
    'Baud', 'Clk Mhz', 'General Timer', 'Perf Timer', 'Cores',
    'Watchdog', 'Watchdog Timeout', 'I/O', 'I/O Count',
    'SPI Out', 'SPI In', 'Uart Out', 'Uart In', 'PWM', 'GPIO Out', 'GPIO In',
    'I/O Buffer', 'Software Interrupts', 'Hardware Bus',
]

# Field index emitted in MHz although the stub stores Hz.
_CLK_FIELD = COLUMNS.index('Clk Mhz')

HERE = Path(__file__).resolve().parent
STUBS_DIR = HERE / 'stubs'
OUT_CSV = HERE / 'summary.csv'


def _hz_to_mhz(hz: str) -> str:
    """'66000000' -> '66' (drop a trailing .0; keep fractional MHz otherwise)."""
    mhz = int(hz) / 1_000_000
    return str(int(mhz)) if mhz.is_integer() else str(mhz)


def parse_stub(name: str) -> list[str]:
    """Turn one stub filename into a list of CSV cell values."""
    fields = name.split('_')
    if len(fields) != len(COLUMNS):
        raise ValueError(
            f'{name!r}: expected {len(COLUMNS)} fields, got {len(fields)}')
    fields[_CLK_FIELD] = _hz_to_mhz(fields[_CLK_FIELD])
    return fields


def build_rows(stubs_dir: Path) -> list[list[str]]:
    """Parse every stub into a row, sorted numerically for stable output."""
    rows = []
    for path in stubs_dir.iterdir():
        if path.is_file() and not path.name.startswith('.'):
            rows.append(parse_stub(path.name))
    rows.sort(key=lambda r: [float(v) for v in r])
    return rows


def render_csv(rows: list[list[str]]) -> str:
    """Render header + rows as ', '-separated text (matches the shipped file)."""
    lines = [', '.join(COLUMNS)]
    lines += [', '.join(r) for r in rows]
    return '\n'.join(lines) + '\n'


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--stubs', type=Path, default=STUBS_DIR,
                    help='directory of stub files (default: ./stubs)')
    ap.add_argument('--out', type=Path, default=OUT_CSV,
                    help='output CSV path (default: ./summary.csv)')
    ap.add_argument('--check', action='store_true',
                    help='do not write; exit 1 if the output is out of date')
    args = ap.parse_args(argv)

    text = render_csv(build_rows(args.stubs))

    if args.check:
        current = args.out.read_text(encoding='utf-8') if args.out.exists() else ''
        if current != text:
            print(f'{args.out} is stale — re-run build_summary.py', file=sys.stderr)
            return 1
        print(f'{args.out} is up to date')
        return 0

    args.out.write_text(text, encoding='utf-8')
    n = text.count('\n') - 1
    print(f'Wrote {n} rows to {args.out}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
