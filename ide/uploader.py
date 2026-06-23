"""ELM11 program upload protocol — runs in a background QThread."""
import logging
import time

log = logging.getLogger(__name__)

from PyQt6.QtCore import QThread, pyqtSignal
import serial

FLASH_PAGE_BYTES = 256
WBUF_RETRY_LIMIT = 3


class UploaderWorker(QThread):
    """Upload a Lua program to the ELM11 over an existing serial.Serial port.

    Signals:
        progress(str)   — status messages (shown in build output)
        finished_ok()   — upload completed successfully
        finished_err(str) — upload failed with reason
    """
    progress     = pyqtSignal(str)
    finished_ok  = pyqtSignal()
    finished_err = pyqtSignal(str)

    _ERROR_CODES = {
        0x10: 'Program file size exceeds maximum supported',
        0x11: 'Attempted to upload program that exceeds proclaimed size',
    }

    def __init__(self, ser: serial.Serial, file_path: str):
        super().__init__()
        self._ser = ser
        self._file_path = file_path

    def run(self):
        try:
            self._do_upload()
        except Exception as exc:
            log.exception('Upload failed')
            self.finished_err.emit(str(exc))

    def _do_upload(self):
        log.debug('Function \'_do_upload\' - begin')

        ser = self._ser

        # ── Read program file ─────────────────────────────────────────────
        with open(self._file_path, 'r') as f:
            bprog = f.read().encode('utf-8')
        prog_len = len(bprog)
        self.progress.emit(f'Read program: {prog_len} bytes\n')

        # ── Establish comms ───────────────────────────────────────────────
        self.progress.emit('Establishing comms with board...\n')
        res = b''
        for i in range(10):
            ser.write(bytes([0x07]))
            time.sleep(0.2)
            res = ser.read()
            if len(res) > 0 and res[0] == 0x06:
                break

        if len(res) == 0 or res[0] != 0x06:
            self.finished_err.emit('Timeout — no response from board')
            return

        self.progress.emit('Comms established\n')
        ser.reset_input_buffer()

        # ── Upload program length ─────────────────────────────────────────
        self.progress.emit('Uploading program metadata...\n')
        ser.write(bytes([0x09]))
        ok, rxval = self._wait_byte(0x08)
        if not ok:
            self.finished_err.emit('Program length handshake failed')
            return

        chksum = 0
        for i in reversed(range(4)):
            b = (prog_len >> (i * 8)) & 0xFF
            ser.write(bytes([b]))
            chksum = (chksum + b) & 0xFF

        ok, rxval = self._wait_byte(chksum)
        if not ok:
            self.finished_err.emit(f'Program length checksum failed (expected {chksum}, got {rxval})')
            return

        ok, rxval = self._wait_byte(0x0A)
        if not ok:
            err = self._ERROR_CODES.get(rxval, f'Unknown error: {rxval:#x}')
            self.finished_err.emit(f'Program length rejected: {err}')
            return

        # ── Upload program data ───────────────────────────────────────────
        self.progress.emit('Uploading program data...\n')
        block = 1
        while len(bprog):
            retries = 0
            while True:
                time.sleep(0.1)
                self.progress.emit(f'  Block {block}...\n')

                ser.write(bytes([0x0C]))
                ok, rxval = self._wait_byte(0x0B)
                if not ok:
                    err = self._ERROR_CODES.get(rxval, f'Unknown error: {rxval:#x}')
                    self.finished_err.emit(f'Block {block} handshake failed: {err}')
                    return

                if self._send_buffer(bprog[:FLASH_PAGE_BYTES]):
                    break
                retries += 1
                if retries > WBUF_RETRY_LIMIT:
                    self.finished_err.emit(f'Block {block}: too many checksum retries')
                    return

            bprog = bprog[FLASH_PAGE_BYTES:]
            block += 1

        ser.write(bytes([0x0D]))
        self.progress.emit(f'\nUpload complete ({block - 1} blocks)\n')
        self.finished_ok.emit()

        log.debug('Function \'_do_upload\' - end')

    def _wait_byte(self, expected: int) -> tuple[bool, int]:
        """Block until a byte is received; return (matched, actual)."""
        resp = b''
        while len(resp) == 0:
            resp = self._ser.read()
        return resp[0] == expected, resp[0]

    def _send_buffer(self, buf: bytes) -> bool:
        """Send a data buffer with length prefix and checksum. Returns True on success."""
        chksum = sum(buf) & 0xFF
        payload = bytes([len(buf) - 1]) + buf
        for b in payload:
            self._ser.write(bytes([b]))
            time.sleep(0.001)

        ok, rxval = self._wait_byte(chksum)
        if not ok:
            self.progress.emit(f'  Checksum mismatch (expected {chksum}, got {rxval})\n')
        return ok
