"""
CAN log: QTableView + model for received (and optionally sent) frames.
Columns: time, direction, ID, extended, RTR, DLC, data (hex).
"""

import time
from PyQt6.QtCore import Qt, QAbstractTableModel, QModelIndex
from PyQt6.QtWidgets import QTableView, QHeaderView

from .protocol import CANFrame


class CANLogModel(QAbstractTableModel):
    """Table model holding (timestamp, direction, CANFrame)."""

    COL_TIME = 0
    COL_DIR = 1
    COL_ID = 2
    COL_EXT = 3
    COL_RTR = 4
    COL_DLC = 5
    COL_DATA = 6
    COL_COUNT = 7

    HEADERS = ("Time", "Dir", "ID", "Ext", "RTR", "DLC", "Data")

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._rows: list[tuple[float, str, CANFrame]] = []  # (ts, "RX"|"TX", frame)
        self._paused = False
        self._max_rows = 10000

    def set_paused(self, paused: bool) -> None:
        self._paused = paused

    def is_paused(self) -> bool:
        return self._paused

    def append_rx(self, frame: CANFrame) -> None:
        if self._paused:
            return
        self._append(time.time(), "RX", frame)

    def append_tx(self, frame: CANFrame) -> None:
        if self._paused:
            return
        self._append(time.time(), "TX", frame)

    def _append(self, ts: float, direction: str, frame: CANFrame) -> None:
        while len(self._rows) >= self._max_rows:
            self.beginRemoveRows(QModelIndex(), 0, 0)
            self._rows.pop(0)
            self.endRemoveRows()
        row = (ts, direction, frame)
        r = len(self._rows)
        self.beginInsertRows(QModelIndex(), r, r)
        self._rows.append(row)
        self.endInsertRows()

    def clear(self) -> None:
        self.beginResetModel()
        self._rows.clear()
        self.endResetModel()

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        if parent.isValid():
            return 0
        return len(self._rows)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        if parent.isValid():
            return 0
        return self.COL_COUNT

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):  # type: ignore[override]
        if not index.isValid() or role != Qt.ItemDataRole.DisplayRole:
            return None
        r, c = index.row(), index.column()
        if r < 0 or r >= len(self._rows):
            return None
        ts, direction, frame = self._rows[r]
        if c == self.COL_TIME:
            return f"{ts:.3f}"
        if c == self.COL_DIR:
            return direction
        if c == self.COL_ID:
            return frame.id_hex()
        if c == self.COL_EXT:
            return "Y" if frame.extended else "N"
        if c == self.COL_RTR:
            return "Y" if frame.rtr else "N"
        if c == self.COL_DLC:
            return str(frame.dlc)
        if c == self.COL_DATA:
            return frame.data_hex()
        return None

    def headerData(
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.ItemDataRole.DisplayRole,
    ):  # type: ignore[override]
        if orientation != Qt.Orientation.Horizontal or role != Qt.ItemDataRole.DisplayRole:
            return None
        if 0 <= section < self.COL_COUNT:
            return self.HEADERS[section]
        return None


class CANLogView(QTableView):
    """Table view for CAN log with auto-scroll and clear/pause."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setModel(CANLogModel(self))
        self.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.setAlternatingRowColors(True)
        h = self.horizontalHeader()
        h.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        h.setStretchLastSection(True)
        self.verticalHeader().setDefaultSectionSize(22)

    def model(self) -> CANLogModel:  # type: ignore[override]
        return super().model()  # type: ignore[return-value]

    def append_rx(self, frame: CANFrame) -> None:
        self.model().append_rx(frame)
        self.scrollToBottom()

    def append_tx(self, frame: CANFrame) -> None:
        self.model().append_tx(frame)
        self.scrollToBottom()

    def clear_log(self) -> None:
        self.model().clear()

    def set_paused(self, paused: bool) -> None:
        self.model().set_paused(paused)

    def is_paused(self) -> bool:
        return self.model().is_paused()
