# Copyright (c) 2026 Hemant Babel
# SPDX-License-Identifier: GPL-3.0-only
"""
Send frame panel: ID (hex), Extended/RTR checkboxes, DLC (0-8), Data (hex). Send button.
"""

from PyQt6.QtCore import QSignalBlocker, pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)


def parse_hex_id(text: str, extended: bool) -> int | None:
    """Parse a hex ID string. Return int or None if invalid."""
    text = text.strip().replace(" ", "").replace("_", "")
    if not text:
        return None
    if text.lower().startswith("0x"):
        text = text[2:]
    if not text:
        return None
    try:
        value = int(text, 16)
        if extended:
            if not 0 <= value <= 0x1FFF_FFFF:
                return None
        elif not 0 <= value <= 0x7FF:
            return None
        return value
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
        value = bytes.fromhex(text)
        if len(value) > 8:
            return None
        return value
    except ValueError:
        return None


class SendFramePanel(QWidget):
    """Panel to compose and send one CAN frame."""

    send_requested = pyqtSignal(int, bool, bool, int, bytes)  # id, extended, rtr, dlc, data

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._transport_enabled = False
        self._show_validation = False

        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(0, 0, 0, 0)

        row = QHBoxLayout()
        row.setSpacing(8)
        row.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(row)

        send_lbl = QLabel("Send")
        send_lbl.setObjectName("sectionTitle")
        row.addWidget(send_lbl)

        row.addWidget(QLabel("ID"))
        self.id_edit = QLineEdit()
        self.id_edit.setPlaceholderText("7DF")
        self.id_edit.setMinimumWidth(96)
        self.id_edit.setMaximumWidth(128)
        row.addWidget(self.id_edit)

        row.addWidget(QLabel("DLC"))
        self.dlc_spin = QSpinBox()
        self.dlc_spin.setRange(0, 8)
        self.dlc_spin.setValue(0)
        self.dlc_spin.setFixedWidth(72)
        row.addWidget(self.dlc_spin)

        self.extended_cb = QCheckBox("Ext")
        self.extended_cb.setToolTip("Extended 29-bit ID")
        row.addWidget(self.extended_cb)

        self.rtr_cb = QCheckBox("RTR")
        row.addWidget(self.rtr_cb)

        row.addWidget(QLabel("Data"))
        self.data_edit = QLineEdit()
        self.data_edit.setPlaceholderText("00 11 22 33 44 55 66 77")
        self.data_edit.setMinimumWidth(320)
        row.addWidget(self.data_edit)

        self.send_btn = QPushButton("Send")
        self.send_btn.setObjectName("primaryBtn")
        self.send_btn.setMinimumWidth(88)
        self.send_btn.clicked.connect(self._on_send)
        row.addWidget(self.send_btn)

        row.addStretch(1)

        self.error_label = QLabel("")
        self.error_label.setObjectName("formError")
        self.error_label.setWordWrap(True)
        layout.addWidget(self.error_label)

        self.id_edit.textChanged.connect(self._update_form_state)
        self.id_edit.textEdited.connect(self._on_user_edit)
        self.data_edit.textChanged.connect(self._on_data_text_changed)
        self.data_edit.textEdited.connect(self._on_user_edit)
        self.extended_cb.toggled.connect(self._update_form_state)
        self.rtr_cb.toggled.connect(self._on_rtr_toggled)
        self.dlc_spin.valueChanged.connect(self._update_form_state)

        self._on_rtr_toggled(self.rtr_cb.isChecked())

    def _on_send(self) -> None:
        self._show_validation = True
        valid, _message, id_value, dlc, data = self._validate_form()
        if not valid:
            self._update_form_state()
            if id_value is None:
                self.id_edit.setFocus()
            else:
                self.data_edit.setFocus()
            return
        self.send_requested.emit(
            id_value,
            self.extended_cb.isChecked(),
            self.rtr_cb.isChecked(),
            dlc,
            data,
        )

    def set_send_enabled(self, enabled: bool) -> None:
        self._transport_enabled = enabled
        self._update_form_state()

    def _on_user_edit(self, _text: str) -> None:
        self._show_validation = True
        self._update_form_state()

    def _on_rtr_toggled(self, checked: bool) -> None:
        self.data_edit.setEnabled(not checked)
        if checked:
            self.data_edit.clear()
            self.dlc_spin.setReadOnly(False)
            self.dlc_spin.setButtonSymbols(QSpinBox.ButtonSymbols.UpDownArrows)
            self.dlc_spin.setProperty("state", "")
        else:
            self.dlc_spin.setReadOnly(True)
            self.dlc_spin.setButtonSymbols(QSpinBox.ButtonSymbols.NoButtons)
            self.dlc_spin.setProperty("state", "locked")
            self._sync_dlc_with_data()
        self._refresh_widget_style(self.data_edit)
        self._refresh_widget_style(self.dlc_spin)
        self._update_form_state()

    def _on_data_text_changed(self) -> None:
        if not self.rtr_cb.isChecked():
            self._sync_dlc_with_data()
        self._update_form_state()

    def _sync_dlc_with_data(self) -> None:
        data = parse_hex_data(self.data_edit.text())
        if data is None:
            return
        blocker = QSignalBlocker(self.dlc_spin)
        self.dlc_spin.setValue(len(data))
        del blocker

    def _validate_form(self) -> tuple[bool, str, int | None, int, bytes]:
        id_value = parse_hex_id(self.id_edit.text(), self.extended_cb.isChecked())
        if id_value is None:
            id_limit = "29-bit hex ID up to 1FFFFFFF" if self.extended_cb.isChecked() else "11-bit hex ID up to 7FF"
            return False, f"Enter a valid {id_limit}.", None, self.dlc_spin.value(), bytes()

        if self.rtr_cb.isChecked():
            return True, "", id_value, self.dlc_spin.value(), bytes()

        data = parse_hex_data(self.data_edit.text())
        if data is None:
            return False, "Enter data as hex byte pairs, up to 8 bytes.", id_value, self.dlc_spin.value(), bytes()
        return True, "", id_value, len(data), data

    def _update_form_state(self) -> None:
        valid, message, id_value, _dlc, _data = self._validate_form()
        data_error = bool(message) and id_value is not None and not self.rtr_cb.isChecked()

        show_errors = self._show_validation
        self.id_edit.setProperty("state", "error" if show_errors and id_value is None else "")
        self.data_edit.setProperty("state", "error" if show_errors and data_error else "")
        self.error_label.setText(message if show_errors else "")
        self.send_btn.setEnabled(self._transport_enabled and valid)

        self._refresh_widget_style(self.id_edit)
        self._refresh_widget_style(self.data_edit)

    def _refresh_widget_style(self, widget: QWidget) -> None:
        widget.style().unpolish(widget)
        widget.style().polish(widget)
        widget.update()


