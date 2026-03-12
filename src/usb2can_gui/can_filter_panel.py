# Copyright (c) 2026 Hemant Babel
# SPDX-License-Identifier: GPL-3.0-only
"""
Right panel: overwrite option, search, and scroll list of unique CAN IDs with visibility controls.
"""

from PyQt6.QtCore import QSignalBlocker, Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)


class CANFilterPanel(QWidget):
    """Overwrite option + list of unique CAN IDs; check = show in log, uncheck = hide."""

    visible_ids_changed = pyqtSignal(object)  # set[int] | None

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._id_checkboxes: dict[int, QCheckBox] = {}
        self._id_counts: dict[int, int] = {}
        self._id_extended: dict[int, bool] = {}

        layout = QVBoxLayout(self)
        layout.setSpacing(6)
        layout.setContentsMargins(0, 0, 0, 0)

        self.overwrite_cb = QCheckBox("Overwrite same ID")
        self.overwrite_cb.setToolTip(
            "When enabled, a new frame with the same CAN ID updates the existing row so you see running changes."
        )
        self.overwrite_cb.setChecked(False)
        layout.addWidget(self.overwrite_cb)

        header_row = QHBoxLayout()
        header_row.setContentsMargins(0, 0, 0, 0)
        header_row.setSpacing(6)
        ids_label = QLabel("Unique CAN IDs")
        ids_label.setObjectName("sectionTitle")
        header_row.addWidget(ids_label)
        header_row.addStretch(1)

        self.select_all_btn = QPushButton("All")
        self.select_all_btn.clicked.connect(lambda: self._set_checked_for_visible(True))
        header_row.addWidget(self.select_all_btn)

        self.select_none_btn = QPushButton("None")
        self.select_none_btn.clicked.connect(lambda: self._set_checked_for_visible(False))
        header_row.addWidget(self.select_none_btn)
        layout.addLayout(header_row)

        hint_label = QLabel("Checked IDs stay visible in the log.")
        hint_label.setObjectName("subtleText")
        layout.addWidget(hint_label)

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Filter IDs (for example 123 or 0x123)")
        self.search_edit.textChanged.connect(self._apply_search_filter)
        layout.addWidget(self.search_edit)

        self._scroll_content = QWidget()
        self._scroll_layout = QVBoxLayout(self._scroll_content)
        self._scroll_layout.setSpacing(2)
        self._scroll_layout.setContentsMargins(0, 0, 0, 0)
        self._empty_ids_label = QLabel("No IDs observed yet.")
        self._empty_ids_label.setObjectName("subtleText")
        self._scroll_layout.addWidget(self._empty_ids_label)
        self._scroll_layout.addStretch()

        scroll = QScrollArea()
        scroll.setWidget(self._scroll_content)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setMinimumWidth(180)
        scroll.setMinimumHeight(220)
        layout.addWidget(scroll)

    def ensure_id(self, can_id: int, extended: bool = False) -> None:
        """Track a CAN ID, update its count, and create a checkbox if needed."""
        is_new = can_id not in self._id_checkboxes
        self._id_counts[can_id] = self._id_counts.get(can_id, 0) + 1
        self._id_extended[can_id] = extended

        if is_new:
            cb = QCheckBox()
            cb.setChecked(True)
            cb.setProperty("can_id", can_id)
            cb.stateChanged.connect(self._on_id_toggled)
            self._id_checkboxes[can_id] = cb
            self._insert_checkbox_sorted(can_id)
            self._empty_ids_label.hide()

        self._update_checkbox_label(can_id)
        self._apply_search_filter()
        if is_new:
            self._emit_visible_ids()

    def get_visible_ids(self) -> set[int] | None:
        if not self._id_checkboxes:
            return None
        return {cid for cid, cb in self._id_checkboxes.items() if cb.isChecked()}

    def clear_ids(self) -> None:
        for cb in self._id_checkboxes.values():
            self._scroll_layout.removeWidget(cb)
            cb.deleteLater()
        self._id_checkboxes.clear()
        self._id_counts.clear()
        self._id_extended.clear()
        self._empty_ids_label.show()
        self.visible_ids_changed.emit(None)

    def _insert_checkbox_sorted(self, can_id: int) -> None:
        cb = self._id_checkboxes[can_id]
        insert_at = self._scroll_layout.count() - 1
        for index in range(self._scroll_layout.count() - 1):
            item = self._scroll_layout.itemAt(index)
            widget = item.widget()
            if widget is None:
                continue
            existing_id = widget.property("can_id")
            if existing_id is not None and can_id < existing_id:
                insert_at = index
                break
        self._scroll_layout.insertWidget(insert_at, cb)

    def _format_can_id(self, can_id: int) -> str:
        if self._id_extended.get(can_id, False):
            return f"0x{can_id:08X}"
        return f"0x{can_id:03X}"

    def _update_checkbox_label(self, can_id: int) -> None:
        checkbox = self._id_checkboxes[can_id]
        checkbox.setText(f"{self._format_can_id(can_id)} ({self._id_counts[can_id]})")

    def _apply_search_filter(self) -> None:
        for can_id, checkbox in self._id_checkboxes.items():
            checkbox.setVisible(self._matches_search(can_id))

    def _matches_search(self, can_id: int) -> bool:
        query = self.search_edit.text().strip().lower().replace("0x", "")
        if not query:
            return True
        return query in self._format_can_id(can_id).lower().replace("0x", "")

    def _set_checked_for_visible(self, checked: bool) -> None:
        for can_id, checkbox in self._id_checkboxes.items():
            if not self._matches_search(can_id):
                continue
            blocker = QSignalBlocker(checkbox)
            checkbox.setChecked(checked)
            del blocker
        self._emit_visible_ids()

    def _on_id_toggled(self) -> None:
        self._emit_visible_ids()

    def _emit_visible_ids(self) -> None:
        if not self._id_checkboxes:
            self.visible_ids_changed.emit(None)
            return
        visible = {cid for cid, cb in self._id_checkboxes.items() if cb.isChecked()}
        self.visible_ids_changed.emit(visible)


