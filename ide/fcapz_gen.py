"""fpgacapZero (fcapz) Embedded Logic Analyzer — codegen only.

Copies the vendored fcapz RTL subset (`ide/fcapz/rtl/`, see
`ide/fcapz/README.md`) into a workspace's `hardware/fcapz/` directory, and
renders a parametrized `fcapz_ela_gowin` instantiation snippet for the user
to paste into their `user.sv` / `user.vhd` by hand. No files the user edits
(`user.sv`/`user.vhd`) are touched, and nothing is probed/captured from
here — that stays a manual OpenOCD + `fcapz` CLI step outside the IDE.
"""
from __future__ import annotations

import shutil
import sys
from dataclasses import dataclass
from pathlib import Path


def _ide_base() -> Path:
    """Root of the bundled `ide` data (dev, PyInstaller, install)."""
    if hasattr(sys, '_MEIPASS'):
        return Path(sys._MEIPASS) / 'ide'
    return Path(__file__).resolve().parent


def vendored_rtl_dir() -> Path:
    """Root of the vendored fcapz RTL subset (`ide/fcapz/rtl/`)."""
    return _ide_base() / 'fcapz' / 'rtl'


# Files needed for `fcapz_ela_gowin` on its own. Paths are relative to
# `vendored_rtl_dir()`. See `ide/fcapz/README.md` for why each is (or
# isn't) here.
_CORE_FILES = [
    'fcapz_version.vh',
    'dff_sync.v',
    'dff_reg_sync.v',
    'reset_sync.v',
    'dpram.v',
    'trig_compare.v',
    'fcapz_ela.v',
    'fcapz_ela_gowin.v',
    'jtag_tap/jtag_tap_gowin.v',
    'jtag_reg_iface_gowin.v',
    'gowin/gw_jtag.v',
]

# Additionally required only when EIO is enabled.
_EIO_FILES = [
    'fcapz_regbus_mux.v',
    'fcapz_eio.v',
]


@dataclass
class FcapzParams:
    instance_name: str = 'u_ela_1'
    sample_width: int = 8
    num_channels: int = 6
    depth: int = 64
    trig_stages: int = 1
    eio_enable: bool = False
    eio_in_width: int = 1
    eio_out_width: int = 1
    hdl: str = 'SystemVerilog'   # 'SystemVerilog' | 'VHDL'


def copy_rtl_into_workspace(workspace_root: Path, include_eio: bool) -> list[Path]:
    """Copy the required vendored RTL files into
    `<workspace_root>/hardware/fcapz/`, preserving the `jtag_tap/`
    subdirectory. Overwrites existing copies (same rationale as
    `MainWindow._deploy_build_templates`: the deployed copy should always
    reflect the IDE's current bundle). Returns the list of destination
    paths written."""
    src_root = vendored_rtl_dir()
    dst_root = workspace_root / 'hardware' / 'fcapz'

    files = list(_CORE_FILES)
    if include_eio:
        files += _EIO_FILES

    written: list[Path] = []
    for rel in files:
        src = src_root / rel
        dst = dst_root / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dst)
        written.append(dst)
    return written


def _sv_snippet(p: FcapzParams) -> str:
    probe_width = p.sample_width * p.num_channels
    eio_ports = ''
    eio_params = ''
    if p.eio_enable:
        eio_params = (
            f",\n    .EIO_EN         ({1}),\n"
            f"    .EIO_IN_W       ({p.eio_in_width}),\n"
            f"    .EIO_OUT_W      ({p.eio_out_width})"
        )
        eio_ports = (
            f",\n    .eio_probe_in   ({p.instance_name}_eio_probe_in),\n"
            f"    .eio_probe_out  ({p.instance_name}_eio_probe_out)"
        )

    lines = [
        '// --- fpgacapZero Embedded Logic Analyzer ---------------------------',
        f'// {p.num_channels} channel(s) x {p.sample_width}-bit, depth {p.depth}.',
        '// TODO: wire tms/tck/tdi/tdo to the JTAG pads once exposed by the',
        '// `emblua` base image and added to this board\'s location.cst.',
        f'wire [{probe_width - 1}:0] {p.instance_name}_probe;',
        '// TODO: assign each channel slot, e.g.:',
        f'//   assign {p.instance_name}_probe = {{ my_signal_b, my_signal_a }};',
    ]
    if p.eio_enable:
        lines += [
            f'wire [{p.eio_in_width - 1}:0] {p.instance_name}_eio_probe_in;',
            f'wire [{p.eio_out_width - 1}:0] {p.instance_name}_eio_probe_out;',
        ]
    lines += [
        '',
        f'fcapz_ela_gowin #(',
        f'    .SAMPLE_W       ({p.sample_width}),',
        f'    .DEPTH          ({p.depth}),',
        f'    .TRIG_STAGES    ({p.trig_stages}),',
        f'    .NUM_CHANNELS   ({p.num_channels}){eio_params}',
        f') {p.instance_name} (',
        '    .clk            (/* TODO: >= ~10x JTAG TCK, e.g. ~2 MHz min */),',
        '',
        '    .jtag_activity  (),',
        '',
        '    .sample_clk     (/* TODO: capture-domain clock */),',
        '    .sample_rst     (/* TODO: capture-domain reset */),',
        '',
        f'    .probe_in       ({p.instance_name}_probe){eio_ports},',
        '',
        '    .tms_pad_i      (tms),',
        '    .tck_pad_i      (tck),',
        '    .tdi_pad_i      (tdi),',
        '    .tdo_pad_o      (tdo)',
        ');',
        '// ---------------------------------------------------------------------',
    ]
    return '\n'.join(lines)


def _vhdl_snippet(p: FcapzParams) -> str:
    probe_width = p.sample_width * p.num_channels
    eio_generics = ''
    eio_ports = ''
    if p.eio_enable:
        eio_generics = (
            f";\n        EIO_EN          : integer := 1;\n"
            f"        EIO_IN_W        : integer := {p.eio_in_width};\n"
            f"        EIO_OUT_W       : integer := {p.eio_out_width}"
        )
        eio_ports = (
            f";\n        eio_probe_in    : in  std_logic_vector({p.eio_in_width - 1} downto 0);\n"
            f"        eio_probe_out   : out std_logic_vector({p.eio_out_width - 1} downto 0)"
        )

    lines = [
        '-- --- fpgacapZero Embedded Logic Analyzer ----------------------------',
        f'-- {p.num_channels} channel(s) x {p.sample_width}-bit, depth {p.depth}.',
        '-- TODO: wire tms/tck/tdi/tdo to the JTAG pads once exposed by the',
        "-- `emblua` base image and added to this board's location.cst.",
        '--',
        '-- Mixed-language binding: `fcapz_ela_gowin` is a Verilog module.',
        '-- Declare it as a VHDL component (once per file) so it can be',
        '-- instantiated below; Gowin EDA binds it by matching component',
        '-- name to module name across the synthesis project.',
        '',
        'component fcapz_ela_gowin is',
        '    generic (',
        '        SAMPLE_W        : integer := 8;',
        '        DEPTH           : integer := 1024;',
        '        TRIG_STAGES     : integer := 1;',
        f'        NUM_CHANNELS    : integer := 1{eio_generics}',
        '    );',
        '    port (',
        '        clk             : in  std_logic;',
        '        jtag_activity   : out std_logic;',
        '        sample_clk      : in  std_logic;',
        '        sample_rst      : in  std_logic;',
        f'        probe_in        : in  std_logic_vector((SAMPLE_W*NUM_CHANNELS)-1 downto 0){eio_ports};',
        '        tms_pad_i       : in  std_logic;',
        '        tck_pad_i       : in  std_logic;',
        '        tdi_pad_i       : in  std_logic;',
        '        tdo_pad_o       : out std_logic',
        '    );',
        'end component;',
        '',
        f'signal {p.instance_name}_probe : std_logic_vector({probe_width - 1} downto 0);',
        '-- TODO: assign each channel slot, e.g.:',
        f'--   {p.instance_name}_probe <= my_signal_b & my_signal_a;',
    ]
    if p.eio_enable:
        lines += [
            f'signal {p.instance_name}_eio_probe_in  : std_logic_vector({p.eio_in_width - 1} downto 0);',
            f'signal {p.instance_name}_eio_probe_out : std_logic_vector({p.eio_out_width - 1} downto 0);',
        ]
    eio_port_map = (
        f",\n        eio_probe_in    => {p.instance_name}_eio_probe_in,\n"
        f"        eio_probe_out   => {p.instance_name}_eio_probe_out"
    ) if p.eio_enable else ''
    lines += [
        '',
        f'{p.instance_name} : fcapz_ela_gowin',
        '    generic map (',
        f'        SAMPLE_W        => {p.sample_width},',
        f'        DEPTH           => {p.depth},',
        f'        TRIG_STAGES     => {p.trig_stages},',
        f'        NUM_CHANNELS    => {p.num_channels}{"," if p.eio_enable else ""}',
    ]
    if p.eio_enable:
        lines += [
            '        EIO_EN          => 1,',
            f'        EIO_IN_W        => {p.eio_in_width},',
            f'        EIO_OUT_W       => {p.eio_out_width}',
        ]
    lines += [
        '    )',
        '    port map (',
        '        clk             => ,  -- TODO: >= ~10x JTAG TCK, e.g. ~2 MHz min',
        '',
        '        jtag_activity   => open,',
        '',
        '        sample_clk      => ,  -- TODO: capture-domain clock',
        '        sample_rst      => ,  -- TODO: capture-domain reset',
        '',
        f'        probe_in        => {p.instance_name}_probe{eio_port_map},',
        '',
        '        tms_pad_i       => tms,',
        '        tck_pad_i       => tck,',
        '        tdi_pad_i       => tdi,',
        '        tdo_pad_o       => tdo',
        '    );',
        '-- ----------------------------------------------------------------------',
    ]
    return '\n'.join(lines)


def generate_snippet(p: FcapzParams) -> str:
    """Render the instantiation snippet text for the given parameters,
    indented one level (4 spaces) since it's pasted inside a module body.
    Blank lines are left bare (no trailing whitespace)."""
    text = _vhdl_snippet(p) if p.hdl == 'VHDL' else _sv_snippet(p)
    return '\n'.join(('    ' + line if line else line)
                      for line in text.split('\n'))
