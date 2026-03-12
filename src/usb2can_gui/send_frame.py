"""
Send frame panel: ID (hex), Extended/RTR checkboxes, DLC (0-8), Data (hex). Send button.
"""

from PyQt6.QtWidgets import (
    QWidget,
    QFormLayout,
    QLineEdit,
    QCheckBox,
    QSpinBox,
    QPushButton,
    QHBoxLayout,
)
from PyQt6.QtCore import pyqtSignal



def parse_hex_id(text: str, extended: bool) -> int | None:
    """Parse hex ID string. Return int or None if invalid."""
    text = text.strip().replace(" ", "")
    if not text:
        return None
    try:
        v = int(text, 16)
        if extended:
            if not 0 <= v <= 0x1FFF_FFFF:
                return None
        else:
            if not 0 <= v <= 0x7FF:
                return None
        return v
    except ValueError:
        return None


def parse_hex_data(text: str) -> bytes | None:
    """Parse hex string to bytes (0-8 bytes). Allow spaces. Return None if invalid."""
    text = text.strip().replace(" ", "")
    if not text:
        return bytes()
    if len(text) % 2:
        return None
    try:
        b = bytes.fromhex(text)
        if len(b) > 8:
            return None
        return b
    except ValueError:
        return None


class SendFramePanel(QWidget):
    """Panel to compose and send one CAN frame."""

    send_requested = pyqtSignal(int, bool, bool, int, bytes)  # id, extended, rtr, dlc, data

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        layout = QFormLayout(self)

        self.id_edit = QLineEdit()
        self.id_edit.setPlaceholderText("e.g. 123 or 18F00")
        self.id_edit.setMaximumWidth(180)
        layout.addRow("ID (hex):", self.id_edit)

        self.extended_cb = QCheckBox("Extended (29-bit)")
        layout.addRow("", self.extended_cb)

        self.rtr_cb = QCheckBox("RTR")
        layout.addRow("", self.rtr_cb)

        self.dlc_spin = QSpinBox()
        self.dlc_spin.setRange(0, 8)
        self.dlc_spin.setValue(8)
        self.dlc_spin.setMaximumWidth(80)
        layout.addRow("DLC:", self.dlc_spin)

        self.data_edit = QLineEdit()
        self.data_edit.setPlaceholderText("00 11 22 33 44 55 66 77")
        self.data_edit.setMaximumWidth(220)
        layout.addRow("Data (hex):", self.data_edit)

        btn_layout = QHBoxLayout()
        self.send_btn = QPushButton("Send")
        self.send_btn.clicked.connect(self._on_send)
        btn_layout.addWidget(self.send_btn)
        btn_layout.addStretch()
        layout.addRow(btn_layout)

        self.setMaximumWidth(280)

    def _on_send(self) -> None:
        id_val = parse_hex_id(self.id_edit.text(), self.extended_cb.isChecked())
        if id_val is None:
            self.id_edit.setFocus()
            return
        dlc = self.dlc_spin.value()
        data = parse_hex_data(self.data_edit.text())
        if data is None:
            self.data_edit.setFocus()
            return
        if not self.rtr_cb.isChecked() and len(data) != dlc:
            # Pad or truncate to dlc
            if len(data) < dlc:
                data = data + bytes(dlc - len(data))
            else:
                data = data[:dlc]
        self.send_requested.emit(
            id_val,
            self.extended_cb.isChecked(),
            self.rtr_cb.isChecked(),
            dlc,
            data,
        )

    def set_send_enabled(self, enabled: bool) -> None:
        self.send_btn.setEnabled(enabled)
