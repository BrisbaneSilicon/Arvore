"""'Generate Logic Analyzer Core...' dialog — fpgacapZero ELA codegen.

Copies the vendored fcapz RTL into the open workspace and renders a
parametrized instantiation snippet into a read-only box the user copies
into `user.sv`/`user.vhd` by hand. See `ide/fcapz_gen.py` and
`ide/fcapz/README.md`.
"""
from __future__ import annotations

from pathlib import Path

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QWidget,
    QLabel, QLineEdit, QSpinBox, QCheckBox, QComboBox, QPushButton,
    QPlainTextEdit, QMessageBox,
)
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QApplication

from . import theme
from . import fcapz_gen


class FcapzGenDialog(QDialog):
    def __init__(self, workspace_root: Path | None, default_hdl: str, parent=None):
        super().__init__(parent)
        self._workspace_root = workspace_root
        self.setWindowTitle('Generate Logic Analyzer Core')
        self.setStyleSheet(theme.dialog_stylesheet(theme.current()))
        self.setMinimumWidth(520)
        self.resize(760, 860)
        self._build_ui(default_hdl)

    def _build_ui(self, default_hdl: str):
        root = QVBoxLayout(self)

        if self._workspace_root is None:
            root.addWidget(QLabel(
                'No workspace is open — RTL can\'t be copied anywhere. '
                'Open a workspace first.'))

        form = QFormLayout()

        self._name = QLineEdit('u_ela_1')
        form.addRow('Instance name:', self._name)

        self._sample_width = QSpinBox()
        self._sample_width.setRange(1, 64)
        self._sample_width.setValue(8)
        self._sample_width.setToolTip('Bit width shared by every channel '
                                       '(fcapz_ela_gowin has no per-channel width).')
        form.addRow('Sample width (bits):', self._sample_width)

        self._channels = QSpinBox()
        self._channels.setRange(1, 64)
        self._channels.setValue(6)
        form.addRow('Channels:', self._channels)

        self._depth = QSpinBox()
        self._depth.setRange(2, 65536)
        self._depth.setValue(64)
        self._depth.setToolTip('Capture buffer depth, in samples. '
                                'A power of two is conventional.')
        form.addRow('Depth:', self._depth)

        self._trig_stages = QSpinBox()
        self._trig_stages.setRange(1, 16)
        self._trig_stages.setValue(1)
        form.addRow('Trigger stages:', self._trig_stages)

        self._eio_enable = QCheckBox('Include Embedded I/O (EIO) core')
        form.addRow('', self._eio_enable)

        self._eio_in_width = QSpinBox()
        self._eio_in_width.setRange(1, 256)
        self._eio_in_width.setValue(1)
        self._eio_in_width.setEnabled(False)
        form.addRow('EIO in width (bits):', self._eio_in_width)

        self._eio_out_width = QSpinBox()
        self._eio_out_width.setRange(1, 256)
        self._eio_out_width.setValue(1)
        self._eio_out_width.setEnabled(False)
        form.addRow('EIO out width (bits):', self._eio_out_width)

        self._eio_enable.toggled.connect(self._eio_in_width.setEnabled)
        self._eio_enable.toggled.connect(self._eio_out_width.setEnabled)

        self._hdl = QComboBox()
        self._hdl.addItems(['SystemVerilog', 'VHDL'])
        self._hdl.setCurrentText(default_hdl if default_hdl in
                                  ('SystemVerilog', 'VHDL') else 'SystemVerilog')
        form.addRow('Target HDL:', self._hdl)

        root.addLayout(form)

        gen_row = QHBoxLayout()
        gen_row.addStretch(1)
        self._generate_btn = QPushButton('Generate')
        self._generate_btn.clicked.connect(self._on_generate)
        gen_row.addWidget(self._generate_btn)
        root.addLayout(gen_row)

        self._status = QLabel('')
        self._status.setWordWrap(True)
        root.addWidget(self._status)

        self._output = QPlainTextEdit()
        self._output.setReadOnly(True)
        self._output.setFont(QFont('monospace'))
        self._output.setPlaceholderText(
            'Generated instantiation snippet will appear here.')
        root.addWidget(self._output)

        bottom_row = QHBoxLayout()
        self._copy_btn = QPushButton('Copy to Clipboard')
        self._copy_btn.setEnabled(False)
        self._copy_btn.clicked.connect(self._on_copy)
        bottom_row.addWidget(self._copy_btn)
        bottom_row.addStretch(1)
        close_btn = QPushButton('Close')
        close_btn.clicked.connect(self.reject)
        bottom_row.addWidget(close_btn)
        root.addLayout(bottom_row)

    def _on_generate(self):
        if self._workspace_root is None:
            QMessageBox.warning(self, 'No Workspace Open',
                'Open a workspace before generating a Logic Analyzer core.')
            return

        include_eio = self._eio_enable.isChecked()
        params = fcapz_gen.FcapzParams(
            instance_name=self._name.text().strip() or 'u_ela_1',
            sample_width=self._sample_width.value(),
            num_channels=self._channels.value(),
            depth=self._depth.value(),
            trig_stages=self._trig_stages.value(),
            eio_enable=include_eio,
            eio_in_width=self._eio_in_width.value(),
            eio_out_width=self._eio_out_width.value(),
            hdl=self._hdl.currentText(),
        )

        try:
            written = fcapz_gen.copy_rtl_into_workspace(
                self._workspace_root, include_eio)
        except OSError as exc:
            QMessageBox.warning(self, 'Copy Failed',
                f'Could not copy fcapz RTL into the workspace:\n{exc}')
            return

        snippet = fcapz_gen.generate_snippet(params)
        self._output.setPlainText(snippet)
        self._copy_btn.setEnabled(True)
        self._status.setText(
            f'Copied {len(written)} RTL file(s) into '
            f'hardware/fcapz/. Paste the snippet below into '
            f'user.{"vhd" if params.hdl == "VHDL" else "sv"}.')

    def _on_copy(self):
        QApplication.clipboard().setText(self._output.toPlainText())
