# Copyright (c) 2026 Hemant Babel
# SPDX-License-Identifier: GPL-3.0-only
"""
CAN log: QTableView + model for received (and optionally sent) frames.
Columns: time, direction, ID, extended, RTR, DLC, data (hex).
Filtering by visible CAN IDs via proxy model.
"""

import csv
from datetime import datetime
from pathlib import Path
import time
from PyQt6.QtCore import Qt, QAbstractTableModel, QModelIndex, QSortFilterProxyModel, pyqtSignal
from PyQt6.QtGui import QBrush, QColor, QFont, QIcon
from PyQt6.QtWidgets import (
    QLabel,
    QTableView,
    QHeaderView,
    QWidget,
    QVBoxLayout,
    QTabWidget,
    QMenu,
    QApplication,
)

from .protocol import CANFrame

# Role for proxy to read frame ID for filtering
FrameIdRole = Qt.ItemDataRole.UserRole + 1
FrameDirRole = Qt.ItemDataRole.UserRole + 2
MONO_FONT = QFont("Consolas")
MONO_FONT.setStyleHint(QFont.StyleHint.Monospace)
MONO_FONT.setFixedPitch(True)
RX_BACKGROUND = QColor("#F4F8FF")
TX_BACKGROUND = QColor("#F4FBF6")
RX_FOREGROUND = QColor("#225C9E")
TX_FOREGROUND = QColor("#2E7D32")


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
        self._overwrite_when_full = True
        self._overwrite_same_id = False  # when True, update existing row with same ID instead of appending

    def set_paused(self, paused: bool) -> None:
        self._paused = paused

    def set_overwrite_when_full(self, overwrite: bool) -> None:
        self._overwrite_when_full = overwrite

    def set_overwrite_same_id(self, overwrite: bool) -> None:
        self._overwrite_same_id = overwrite

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
        if self._overwrite_same_id:
            for r in range(len(self._rows) - 1, -1, -1):
                if self._rows[r][2].id == frame.id:
                    self._rows[r] = (ts, direction, frame)
                    self.dataChanged.emit(
                        self.index(r, 0),
                        self.index(r, self.COL_COUNT - 1),
                    )
                    return
        if len(self._rows) >= self._max_rows and not self._overwrite_when_full:
            return
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

    def frame_at(self, row: int) -> CANFrame | None:
        if row < 0 or row >= len(self._rows):
            return None
        return self._rows[row][2]

    def to_csv_rows(self) -> list[list[str]]:
        rows: list[list[str]] = []
        for ts, direction, frame in self._rows:
            whole = int(ts)
            ms = int(round((ts - whole) * 1000))
            if ms == 1000:
                whole += 1
                ms = 0
            time_text = f"{time.strftime('%H:%M:%S', time.localtime(whole))}.{ms:03d}"
            rows.append(
                [
                    time_text,
                    direction,
                    frame.id_hex(),
                    "Y" if frame.extended else "-",
                    "Y" if frame.rtr else "-",
                    str(frame.dlc),
                    frame.data_hex(),
                ]
            )
        return rows

    def load_csv_rows(self, records: list[dict[str, str]]) -> int:
        new_rows: list[tuple[float, str, CANFrame]] = []
        now = time.time()
        for record in records:
            try:
                direction = (record.get("Dir", "RX") or "RX").strip().upper()
                if direction not in ("RX", "TX"):
                    continue
                id_text = (record.get("ID", "") or "").strip()
                can_id = int(id_text, 16)
                extended = ((record.get("Ext", "") or "").strip().upper() == "Y")
                rtr = ((record.get("RTR", "") or "").strip().upper() == "Y")
                dlc_text = (record.get("DLC", "") or "").strip()
                dlc = int(dlc_text) if dlc_text else 0
                dlc = max(0, min(8, dlc))
                data_text = (record.get("Data", "") or "").strip()
                data = bytes.fromhex(data_text) if data_text else b""
                data = (data + bytes(8))[:8]
                time_text = (record.get("Time", "") or "").strip()
                ts = self._parse_time_of_day(time_text, now)
                new_rows.append(
                    (
                        ts,
                        direction,
                        CANFrame(
                            id=can_id,
                            extended=extended,
                            rtr=rtr,
                            dlc=dlc,
                            data=data,
                        ),
                    )
                )
            except (TypeError, ValueError):
                continue

        self.beginResetModel()
        self._rows = new_rows
        self.endResetModel()
        return len(new_rows)

    @staticmethod
    def _parse_time_of_day(text: str, fallback_ts: float) -> float:
        try:
            t = datetime.strptime(text, "%H:%M:%S.%f").time()
            today = datetime.now()
            dt = datetime(
                year=today.year,
                month=today.month,
                day=today.day,
                hour=t.hour,
                minute=t.minute,
                second=t.second,
                microsecond=t.microsecond,
            )
            return dt.timestamp()
        except ValueError:
            return fallback_ts

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        if parent.isValid():
            return 0
        return len(self._rows)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        if parent.isValid():
            return 0
        return self.COL_COUNT

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):  # type: ignore[override]
        if not index.isValid():
            return None
        r, c = index.row(), index.column()
        if r < 0 or r >= len(self._rows):
            return None
        ts, direction, frame = self._rows[r]
        if role == FrameIdRole:
            return frame.id
        if role == FrameDirRole:
            return direction
        if role == Qt.ItemDataRole.TextAlignmentRole:
            if c in (self.COL_TIME, self.COL_ID, self.COL_DLC):
                return int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            if c in (self.COL_DIR, self.COL_EXT, self.COL_RTR):
                return int(Qt.AlignmentFlag.AlignCenter)
            return int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        if role == Qt.ItemDataRole.FontRole and c in (self.COL_ID, self.COL_DATA):
            return MONO_FONT
        if role == Qt.ItemDataRole.BackgroundRole:
            return QBrush(RX_BACKGROUND if direction == "RX" else TX_BACKGROUND)
        if role == Qt.ItemDataRole.ForegroundRole and c == self.COL_DIR:
            return QBrush(RX_FOREGROUND if direction == "RX" else TX_FOREGROUND)
        if role != Qt.ItemDataRole.DisplayRole:
            return None
        if c == self.COL_TIME:
            whole = int(ts)
            ms = int(round((ts - whole) * 1000))
            if ms == 1000:
                whole += 1
                ms = 0
            return f"{time.strftime('%H:%M:%S', time.localtime(whole))}.{ms:03d}"
        if c == self.COL_DIR:
            return direction
        if c == self.COL_ID:
            return frame.id_hex()
        if c == self.COL_EXT:
            return "Y" if frame.extended else "-"
        if c == self.COL_RTR:
            return "Y" if frame.rtr else "-"
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


class CANLogFilterProxy(QSortFilterProxyModel):
    """Filter rows by visible CAN IDs. None means no filter state yet."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._visible_ids: set[int] | None = None

    def set_visible_ids(self, ids: set[int] | None) -> None:
        self._visible_ids = ids
        self.invalidateFilter()

    def filterAcceptsRow(self, source_row: int, source_parent: QModelIndex) -> bool:
        if self._visible_ids is None:
            return True
        if not self._visible_ids:
            return False
        idx = self.sourceModel().index(source_row, CANLogModel.COL_ID, source_parent)
        can_id = self.sourceModel().data(idx, FrameIdRole)
        return can_id is not None and can_id in self._visible_ids


class DirectionFilterProxy(CANLogFilterProxy):
    """Filter rows by visible IDs and direction ('RX' or 'TX')."""

    def __init__(self, direction: str, parent=None) -> None:
        super().__init__(parent)
        self._direction = direction

    def filterAcceptsRow(self, source_row: int, source_parent: QModelIndex) -> bool:
        if not super().filterAcceptsRow(source_row, source_parent):
            return False
        idx = self.sourceModel().index(source_row, CANLogModel.COL_DIR, source_parent)
        return self.sourceModel().data(idx, FrameDirRole) == self._direction


class CANLogView(QWidget):
    """Tabbed CAN log with separate RX/TX tables and RX resend context action."""

    resend_requested = pyqtSignal(object)  # CANFrame

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._icons_root = Path(__file__).resolve().parents[2] / "assets" / "icons"
        self._source_model = CANLogModel(self)
        self._auto_scroll = True
        self._rx_proxy = DirectionFilterProxy("RX", self)
        self._tx_proxy = DirectionFilterProxy("TX", self)
        self._rx_proxy.setSourceModel(self._source_model)
        self._tx_proxy.setSourceModel(self._source_model)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self._tabs = QTabWidget(self)
        self._rx_table = self._build_table(self._rx_proxy)
        self._tx_table = self._build_table(self._tx_proxy)
        self._tabs.addTab(self._rx_table, "RX")
        self._tabs.addTab(self._tx_table, "TX")
        self._tabs.setTabIcon(0, self._icon("rx.svg"))
        self._tabs.setTabIcon(1, self._icon("tx.svg"))
        layout.addWidget(self._tabs)

        self._rx_empty_hint = QLabel("No received frames yet.", self._rx_table.viewport())
        self._rx_empty_hint.setObjectName("emptyState")
        self._rx_empty_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._rx_empty_hint.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

        self._tx_empty_hint = QLabel("No transmitted frames yet.", self._tx_table.viewport())
        self._tx_empty_hint.setObjectName("emptyState")
        self._tx_empty_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._tx_empty_hint.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

        self._rx_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._rx_table.customContextMenuRequested.connect(
            lambda pos: self._show_context_menu(self._rx_table, self._rx_proxy, pos, allow_resend=True)
        )
        self._tx_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._tx_table.customContextMenuRequested.connect(
            lambda pos: self._show_context_menu(self._tx_table, self._tx_proxy, pos, allow_resend=False)
        )

        self._rx_proxy.modelReset.connect(self._refresh_empty_hints)
        self._rx_proxy.rowsInserted.connect(self._refresh_empty_hints)
        self._rx_proxy.rowsRemoved.connect(self._refresh_empty_hints)
        self._tx_proxy.modelReset.connect(self._refresh_empty_hints)
        self._tx_proxy.rowsInserted.connect(self._refresh_empty_hints)
        self._tx_proxy.rowsRemoved.connect(self._refresh_empty_hints)
        self._refresh_empty_hints()

    def _build_table(self, proxy: QSortFilterProxyModel) -> QTableView:
        table = QTableView(self)
        table.setModel(proxy)
        table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        table.setAlternatingRowColors(True)
        table.setWordWrap(False)
        table.setShowGrid(False)
        h = table.horizontalHeader()
        h.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        h.setSectionResizeMode(CANLogModel.COL_DATA, QHeaderView.ResizeMode.Stretch)
        table.setColumnWidth(CANLogModel.COL_TIME, 110)
        table.setColumnWidth(CANLogModel.COL_DIR, 56)
        table.setColumnWidth(CANLogModel.COL_ID, 96)
        table.setColumnWidth(CANLogModel.COL_EXT, 52)
        table.setColumnWidth(CANLogModel.COL_RTR, 52)
        table.setColumnWidth(CANLogModel.COL_DLC, 56)
        table.verticalHeader().setVisible(False)
        table.verticalHeader().setDefaultSectionSize(24)
        return table

    def source_model(self) -> CANLogModel:
        return self._source_model

    def set_visible_ids(self, ids: set[int] | None) -> None:
        self._rx_proxy.set_visible_ids(ids)
        self._tx_proxy.set_visible_ids(ids)
        self._refresh_empty_hints()

    def append_rx(self, frame: CANFrame) -> None:
        self._source_model.append_rx(frame)
        if self._auto_scroll:
            self._rx_table.scrollToBottom()
        self._refresh_empty_hints()

    def append_tx(self, frame: CANFrame) -> None:
        self._source_model.append_tx(frame)
        if self._auto_scroll:
            self._tx_table.scrollToBottom()
        self._refresh_empty_hints()

    def clear_log(self) -> None:
        self._source_model.clear()
        self._refresh_empty_hints()

    def save_csv(self, path: str) -> None:
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(CANLogModel.HEADERS)
            writer.writerows(self._source_model.to_csv_rows())

    def load_csv(self, path: str) -> int:
        with open(path, "r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            loaded = self._source_model.load_csv_rows(list(reader))
        self._refresh_empty_hints()
        return loaded

    def set_paused(self, paused: bool) -> None:
        self._source_model.set_paused(paused)

    def is_paused(self) -> bool:
        return self._source_model.is_paused()

    def set_overwrite_when_full(self, overwrite: bool) -> None:
        self._source_model.set_overwrite_when_full(overwrite)

    def set_overwrite_same_id(self, overwrite: bool) -> None:
        self._source_model.set_overwrite_same_id(overwrite)

    def set_auto_scroll(self, enabled: bool) -> None:
        self._auto_scroll = enabled

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._rx_empty_hint.setGeometry(self._rx_table.viewport().rect())
        self._tx_empty_hint.setGeometry(self._tx_table.viewport().rect())
        self._refresh_empty_hints()

    def _refresh_empty_hints(self) -> None:
        self._rx_empty_hint.setVisible(self._rx_proxy.rowCount() == 0)
        self._tx_empty_hint.setVisible(self._tx_proxy.rowCount() == 0)

    def _show_context_menu(
        self,
        table: QTableView,
        proxy: QSortFilterProxyModel,
        pos,
        allow_resend: bool,
    ) -> None:
        idx = table.indexAt(pos)
        if not idx.isValid():
            return
        source_idx = proxy.mapToSource(idx.siblingAtColumn(0))
        frame = self._source_model.frame_at(source_idx.row())
        if frame is None:
            return
        menu = QMenu(table)
        copy_full_action = menu.addAction("Copy Full Frame")
        copy_full_action.setIcon(self._icon("copy.svg"))
        copy_selected_action = menu.addAction("Copy Selected Section")
        copy_selected_action.setIcon(self._icon("copy.svg"))
        send_action = menu.addAction("Send This Frame") if allow_resend else None
        if send_action is not None:
            send_action.setIcon(self._icon("tx.svg"))
        chosen = menu.exec(table.viewport().mapToGlobal(pos))
        if chosen == copy_full_action:
            full_text = "\t".join(
                str(proxy.data(proxy.index(idx.row(), c), Qt.ItemDataRole.DisplayRole) or "")
                for c in range(CANLogModel.COL_COUNT)
            )
            QApplication.clipboard().setText(full_text)
            return
        if chosen == copy_selected_action:
            selected_text = str(idx.data(Qt.ItemDataRole.DisplayRole) or "")
            QApplication.clipboard().setText(selected_text)
            return
        if send_action is not None and chosen == send_action:
            self.resend_requested.emit(frame)

    def _icon(self, name: str) -> QIcon:
        return QIcon(str(self._icons_root / name))


