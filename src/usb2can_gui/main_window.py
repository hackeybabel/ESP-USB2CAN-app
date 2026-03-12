# Copyright (c) 2026 Hemant Babel
# SPDX-License-Identifier: GPL-3.0-only
"""
Main window: Material-style light UI with connection card, CAN log card, send panel card.
"""

import time
from pathlib import Path
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QComboBox,
    QPushButton,
    QLabel,
    QSplitter,
    QStatusBar,
    QMessageBox,
    QCheckBox,
    QProgressBar,
    QFrame,
    QSizePolicy,
    QFileDialog,
    QDialog,
    QDialogButtonBox,
    QPlainTextEdit,
)
from PyQt6.QtCore import Qt, QTimer
from .bridge import Bridge, list_ports
from .can_log import CANLogView
from .can_filter_panel import CANFilterPanel
from .send_frame import SendFramePanel
from .bus_load import BusLoadCalculator
from .styles import get_stylesheet
from .protocol import BAUD_INDEX_TO_RATE, CANFrame


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self._project_root = Path(__file__).resolve().parents[2]
        self.setWindowTitle("ESP-USB2CAN - 3shulmotors")
        self.setWindowIcon(self._icon("branding/app-icon-bridge-mark.svg"))
        self.setMinimumSize(760, 620)
        self.resize(980, 700)
        self.setStyleSheet(get_stylesheet())

        self._bridge = Bridge(self)
        self._bridge.ack_received.connect(self._on_ack)
        self._bridge.frame_received.connect(self._on_frame)
        self._bridge.error.connect(self._on_error)

        self._bus_load = BusLoadCalculator(baud_index=2, window_sec=1.0)
        self._load_update_timer = QTimer(self)
        self._load_update_timer.timeout.connect(self._update_bus_load_display)
        self._load_update_timer.setInterval(250)
        self._dummy_timer = QTimer(self)
        self._dummy_timer.setInterval(100)
        self._dummy_timer.timeout.connect(self._emit_dummy_frame)
        self._dummy_ids = [0x100 + i for i in range(10)]
        self._dummy_index = 0
        self._dummy_seq = 0
        self._auto_scroll_before_overwrite = True

        central = QWidget()
        central.setObjectName("central")
        layout = QVBoxLayout(central)
        layout.setSpacing(8)
        layout.setContentsMargins(12, 10, 12, 10)

        # Connection strip.
        conn_card = QFrame()
        conn_card.setObjectName("cardCompact")
        conn_layout = QVBoxLayout(conn_card)
        conn_layout.setSpacing(8)
        conn_layout.setContentsMargins(12, 10, 12, 10)

        conn_row_top = QHBoxLayout()
        conn_row_top.setSpacing(10)

        conn_row_top.addWidget(QLabel("Port"))
        self.port_combo = QComboBox()
        self.port_combo.setMinimumWidth(120)
        self.port_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        conn_row_top.addWidget(self.port_combo, 1)

        conn_row_top.addWidget(QLabel("Baud"))
        self.baud_combo = QComboBox()
        for i, rate in enumerate(BAUD_INDEX_TO_RATE):
            self.baud_combo.addItem(f"{rate // 1000} kbit/s", i)
        self.baud_combo.setCurrentIndex(2)
        self.baud_combo.setMinimumWidth(80)
        conn_row_top.addWidget(self.baud_combo)

        self.loopback_cb = QCheckBox("Loopback")
        self.loopback_cb.setToolTip("TWAI self-test / self-reception for local bring-up.")
        conn_row_top.addWidget(self.loopback_cb)

        self.connect_btn = QPushButton("Connect")
        self.connect_btn.setObjectName("primaryBtn")
        self.connect_btn.setIcon(self._icon("icons/connect.svg"))
        self.connect_btn.clicked.connect(self._on_connect)

        self.disconnect_btn = QPushButton("Disconnect")
        self.disconnect_btn.setObjectName("secondaryBtn")
        self.disconnect_btn.setIcon(self._icon("icons/disconnect.svg"))
        self.disconnect_btn.clicked.connect(self._on_disconnect)
        self.disconnect_btn.setEnabled(False)

        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.setObjectName("textBtn")
        self.refresh_btn.setIcon(self._icon("icons/refresh.svg"))
        self.refresh_btn.clicked.connect(self._refresh_ports)

        conn_layout.addLayout(conn_row_top)

        conn_row_bottom = QHBoxLayout()
        conn_row_bottom.setSpacing(10)

        conn_row_bottom.addWidget(self.connect_btn)
        conn_row_bottom.addWidget(self.disconnect_btn)
        conn_row_bottom.addWidget(self.refresh_btn)
        conn_row_bottom.addStretch(1)

        self.state_chip = QLabel("Disconnected")
        self.state_chip.setObjectName("connectionState")
        conn_row_bottom.addWidget(self.state_chip)

        conn_row_bottom.addWidget(QLabel("Load"))
        self.bus_load_bar = QProgressBar()
        self.bus_load_bar.setRange(0, 100)
        self.bus_load_bar.setValue(0)
        self.bus_load_bar.setFixedSize(120, 16)
        self.bus_load_bar.setFormat("%v%")
        self.bus_load_bar.setTextVisible(True)
        conn_row_bottom.addWidget(self.bus_load_bar)
        self.bus_load_label = QLabel("--% (-- fps)")
        self.bus_load_label.setToolTip("Bus load and frames/sec over last 1 s.")
        self.bus_load_label.setObjectName("subtleText")
        conn_row_bottom.addWidget(self.bus_load_label)
        conn_layout.addLayout(conn_row_bottom)

        layout.addWidget(conn_card)

        # Main: CAN data (log + filter) + adjustable send panel at bottom.
        main_splitter = QSplitter(Qt.Orientation.Vertical)
        main_splitter.setChildrenCollapsible(True)
        main_splitter.setMinimumHeight(240)

        # Content: log card (left) + filter panel (right)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)

        log_card = QFrame()
        log_card.setObjectName("card")
        log_card_layout = QVBoxLayout(log_card)
        log_card_layout.setContentsMargins(8, 8, 8, 8)
        log_card_layout.setSpacing(6)

        log_header = QHBoxLayout()
        log_title = QLabel("CAN log")
        log_title.setObjectName("sectionTitle")
        log_header.addWidget(log_title)
        log_header.addStretch()
        self.clear_btn = QPushButton("Clear")
        self.clear_btn.clicked.connect(self._on_clear_log)
        log_header.addWidget(self.clear_btn)
        self.pause_cb = QCheckBox("Pause")
        self.pause_cb.stateChanged.connect(
            lambda s: self.can_log.set_paused(s == Qt.CheckState.Checked.value)
        )
        log_header.addWidget(self.pause_cb)
        self.auto_scroll_cb = QCheckBox("Auto-scroll")
        self.auto_scroll_cb.setChecked(True)
        self.auto_scroll_cb.stateChanged.connect(
            lambda s: self.can_log.set_auto_scroll(s == Qt.CheckState.Checked.value)
        )
        log_header.addWidget(self.auto_scroll_cb)
        log_card_layout.addLayout(log_header)

        self.can_log = CANLogView()
        self.can_log.resend_requested.connect(self._on_resend_frame)
        log_card_layout.addWidget(self.can_log)

        splitter.addWidget(log_card)

        # Right panel: overwrite option + unique CAN IDs (show/hide in log).
        filter_card = QFrame()
        filter_card.setObjectName("card")
        filter_card_layout = QVBoxLayout(filter_card)
        filter_card_layout.setContentsMargins(8, 8, 8, 8)
        filter_card_layout.setSpacing(6)
        filter_title = QLabel("Filter and IDs")
        filter_title.setObjectName("sectionTitle")
        filter_card_layout.addWidget(filter_title)

        self.filter_panel = CANFilterPanel(self)
        self.filter_panel.overwrite_cb.stateChanged.connect(self._on_overwrite_mode_toggled)
        self.filter_panel.visible_ids_changed.connect(self.can_log.set_visible_ids)
        filter_card_layout.addWidget(self.filter_panel)

        splitter.addWidget(filter_card)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 0)

        main_splitter.addWidget(splitter)

        # Send section.
        send_card = QFrame()
        send_card.setObjectName("card")
        send_card.setMinimumHeight(92)
        send_card_layout = QVBoxLayout(send_card)
        send_card_layout.setContentsMargins(8, 8, 8, 8)
        send_card_layout.setSpacing(0)
        self.send_panel = SendFramePanel(self)
        self.send_panel.send_requested.connect(self._on_send_frame)
        self.send_panel.set_send_enabled(False)
        send_card_layout.addWidget(self.send_panel)
        main_splitter.addWidget(send_card)

        main_splitter.setStretchFactor(0, 1)
        main_splitter.setStretchFactor(1, 0)
        main_splitter.setSizes([10000, 128])
        layout.addWidget(main_splitter)

        self.setCentralWidget(central)

        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self._init_menu()
        self._set_connection_state("disconnected", "Disconnected", "Disconnected")
        self._refresh_ports()

    def _refresh_ports(self) -> None:
        current_port = self.port_combo.currentData()
        self.port_combo.clear()
        for port, desc in list_ports():
            self.port_combo.addItem(f"{port} - {desc}", port)
        if self.port_combo.count():
            index = self.port_combo.findData(current_port)
            self.port_combo.setCurrentIndex(index if index >= 0 else 0)
        if not self._bridge.is_connected():
            has_ports = self.port_combo.count() > 0
            self.connect_btn.setText("Connect")
            self.connect_btn.setEnabled(has_ports)
            self.disconnect_btn.setEnabled(False)
            self.refresh_btn.setEnabled(True)
            self.port_combo.setEnabled(has_ports)
            self.baud_combo.setEnabled(True)
            self.loopback_cb.setEnabled(True)
            if not has_ports:
                self.status.showMessage("No serial ports found")

    def _on_connect(self) -> None:
        if not self._bridge.is_connected():
            port = self.port_combo.currentData()
            if not port:
                self.status.showMessage("No port selected")
                return
            if not self._bridge.connect(port):
                return
        self.connect_btn.setText("Retry")
        self.connect_btn.setEnabled(False)
        self.disconnect_btn.setEnabled(True)
        self.port_combo.setEnabled(False)
        self.baud_combo.setEnabled(False)
        self.loopback_cb.setEnabled(False)
        self.refresh_btn.setEnabled(False)
        self._set_connection_state("connecting", "Connecting", "Opening CAN interface...")
        idx = self.baud_combo.currentData()
        self._bus_load.set_baud_index(idx)
        self._bus_load.reset()
        self._bridge.set_baud(idx)
        self._bridge.set_loopback(self.loopback_cb.isChecked())
        self._bridge.open_can()
        self._load_update_timer.start()

    def _on_ack(self, ok: bool) -> None:
        if ok:
            self._set_connection_state("ready", "CAN ready", "Connected, CAN ready")
            self.send_panel.set_send_enabled(True)
            self.connect_btn.setEnabled(False)
            self.disconnect_btn.setEnabled(True)
            self.baud_combo.setEnabled(False)
            self.loopback_cb.setEnabled(False)
        else:
            self._set_connection_state("error", "Error", "CAN open failed. Adjust settings and retry.")
            self.send_panel.set_send_enabled(False)
            self.connect_btn.setText("Retry")
            self.connect_btn.setEnabled(True)
            self.disconnect_btn.setEnabled(True)
            self.port_combo.setEnabled(False)
            self.baud_combo.setEnabled(True)
            self.loopback_cb.setEnabled(True)
            QMessageBox.warning(self, "USB2CAN", "Device returned error (ACK ERR). Check baud and bus.")

    def _on_frame(self, frame) -> None:
        self._bus_load.add_frame(frame, time.time())
        self.filter_panel.ensure_id(frame.id, frame.extended)
        self.can_log.append_rx(frame)

    def _on_send_frame(self, id: int, extended: bool, rtr: bool, dlc: int, data: bytes) -> None:
        self._bridge.send_frame(id, extended, rtr, dlc, data)
        pad = data + bytes(8 - len(data))
        frame = CANFrame(id=id, extended=extended, rtr=rtr, dlc=dlc, data=pad[:8])
        self._bus_load.add_frame(frame, time.time())
        self.filter_panel.ensure_id(frame.id, frame.extended)
        self.can_log.append_tx(frame)

    def _on_resend_frame(self, frame) -> None:
        if not self._bridge.is_can_open():
            QMessageBox.warning(self, "USB2CAN", "CAN is not open. Connect first to resend frames.")
            return
        payload = frame.data[: frame.dlc] if not frame.rtr else bytes()
        self._on_send_frame(frame.id, frame.extended, frame.rtr, frame.dlc, payload)

    def _on_disconnect(self) -> None:
        self._load_update_timer.stop()
        self.bus_load_bar.setValue(0)
        self.bus_load_label.setText("--% (-- fps)")
        self._bridge.close_can()
        self._bridge.disconnect()
        self.send_panel.set_send_enabled(False)
        has_ports = self.port_combo.count() > 0
        self.connect_btn.setText("Connect")
        self.connect_btn.setEnabled(has_ports)
        self.disconnect_btn.setEnabled(False)
        self.refresh_btn.setEnabled(True)
        self.port_combo.setEnabled(has_ports)
        self.baud_combo.setEnabled(True)
        self.loopback_cb.setEnabled(True)
        self._set_connection_state("disconnected", "Disconnected", "Disconnected")

    def _on_error(self, msg: str) -> None:
        QMessageBox.warning(self, "USB2CAN", msg)
        if self._bridge.is_connected():
            self._load_update_timer.stop()
            self._bridge.disconnect()
            self.send_panel.set_send_enabled(False)
            self.bus_load_bar.setValue(0)
            self.bus_load_label.setText("--% (-- fps)")
        has_ports = self.port_combo.count() > 0
        self.connect_btn.setText("Connect")
        self.connect_btn.setEnabled(has_ports)
        self.disconnect_btn.setEnabled(False)
        self.refresh_btn.setEnabled(True)
        self.port_combo.setEnabled(has_ports)
        self.baud_combo.setEnabled(True)
        self.loopback_cb.setEnabled(True)
        self._set_connection_state("error", "Error", f"Error: {msg}")

    def _update_bus_load_display(self) -> None:
        if not self._bridge.is_can_open():
            return
        snap = self._bus_load.get_snapshot()
        self.bus_load_bar.setValue(int(round(snap.load_percent)))
        self.bus_load_label.setText(f"{snap.load_percent:.1f}% ({snap.frames_per_sec:.0f} fps)")

    def _on_clear_log(self) -> None:
        self.can_log.clear_log()
        self.filter_panel.clear_ids()

    def _on_overwrite_mode_toggled(self, state: int) -> None:
        enabled = state == Qt.CheckState.Checked.value
        self.can_log.set_overwrite_same_id(enabled)
        if enabled:
            self._auto_scroll_before_overwrite = self.auto_scroll_cb.isChecked()
            self.can_log.clear_log()
            self.filter_panel.clear_ids()
            self.auto_scroll_cb.setChecked(False)
            self.auto_scroll_cb.setEnabled(False)
            return
        self.auto_scroll_cb.setEnabled(True)
        self.auto_scroll_cb.setChecked(self._auto_scroll_before_overwrite)

    def closeEvent(self, event) -> None:
        if self._bridge.is_connected():
            self._bridge.disconnect()
        event.accept()

    def _init_menu(self) -> None:
        menu = self.menuBar()

        file_menu = menu.addMenu("File")
        open_log_action = file_menu.addAction("Open Log")
        save_log_action = file_menu.addAction("Save Log")
        open_log_action.triggered.connect(self._on_open_log)
        save_log_action.triggered.connect(self._on_save_log)

        view_menu = menu.addMenu("View")
        self.dummy_frames_action = view_menu.addAction("Dummy Frames")
        self.dummy_frames_action.setIcon(self._icon("icons/dummy-frames.svg"))
        self.dummy_frames_action.setCheckable(True)
        self.dummy_frames_action.toggled.connect(self._on_dummy_frames_toggled)

        about_menu = menu.addMenu("About")
        license_action = about_menu.addAction("LICENSE")
        about_action = about_menu.addAction("ABOUT")
        license_action.setIcon(self._icon("icons/license.svg"))
        about_action.setIcon(self._icon("icons/about.svg"))
        license_action.triggered.connect(self._on_show_license)
        about_action.triggered.connect(self._on_show_about)

    def _on_dummy_frames_toggled(self, enabled: bool) -> None:
        if enabled:
            self._dummy_timer.start()
            self.status.showMessage("Dummy frames enabled (10 CAN IDs, 100 ms interval)")
            return
        self._dummy_timer.stop()
        self.status.showMessage("Dummy frames disabled")

    def _emit_dummy_frame(self) -> None:
        can_id = self._dummy_ids[self._dummy_index]
        self._dummy_index = (self._dummy_index + 1) % len(self._dummy_ids)
        dlc = (self._dummy_seq % 8) + 1
        payload = bytes((self._dummy_seq + i) & 0xFF for i in range(8))
        self._dummy_seq = (self._dummy_seq + 1) & 0xFF
        frame = CANFrame(id=can_id, extended=False, rtr=False, dlc=dlc, data=payload)
        self._on_frame(frame)

    def _on_open_log(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Open CAN Log",
            "",
            "CSV Files (*.csv);;All Files (*)",
        )
        if not path:
            return
        try:
            loaded = self.can_log.load_csv(path)
            self.filter_panel.clear_ids()
            self.status.showMessage(f"Loaded {loaded} log rows from {Path(path).name}")
        except Exception as e:
            QMessageBox.warning(self, "Open Log", f"Failed to open log: {e}")

    def _on_save_log(self) -> None:
        default_name = f"can-log-{time.strftime('%Y%m%d-%H%M%S')}.csv"
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Save CAN Log",
            default_name,
            "CSV Files (*.csv);;All Files (*)",
        )
        if not path:
            return
        try:
            self.can_log.save_csv(path)
            self.status.showMessage(f"Saved log to {Path(path).name}")
        except Exception as e:
            QMessageBox.warning(self, "Save Log", f"Failed to save log: {e}")

    def _on_show_license(self) -> None:
        candidates = ("LICENSE", "LICENSE.txt", "license.txt")
        text = None
        for name in candidates:
            p = self._project_root / name
            if p.exists():
                text = p.read_text(encoding="utf-8", errors="replace")
                break
        if text is None:
            text = "No LICENSE file found in project root."
        self._show_text_dialog("LICENSE", text)

    def _on_show_about(self) -> None:
        QMessageBox.information(
            self,
            "ABOUT",
            "ESP-USB2CAN\nDeveloped by Hemant Babel\n"
            "PyQt6 desktop app for ESP32-C3 USB-to-CAN bridge.\n"
            "Supports live RX/TX logging, filtering, and frame transmission.",
        )

    def _show_text_dialog(self, title: str, text: str) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle(title)
        dialog.resize(760, 560)
        layout = QVBoxLayout(dialog)

        text_view = QPlainTextEdit(dialog)
        text_view.setReadOnly(True)
        text_view.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        text_view.setPlainText(text)
        layout.addWidget(text_view)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close, parent=dialog)
        buttons.rejected.connect(dialog.reject)
        buttons.accepted.connect(dialog.accept)
        layout.addWidget(buttons)

        dialog.exec()

    def _set_connection_state(self, state: str, label: str, status_message: str | None = None) -> None:
        self.state_chip.setProperty("state", state)
        self.state_chip.setText(label)
        self.state_chip.style().unpolish(self.state_chip)
        self.state_chip.style().polish(self.state_chip)
        self.state_chip.update()
        if status_message is not None:
            self.status.showMessage(status_message)

    def _icon(self, relative_asset_path: str) -> QIcon:
        return QIcon(str(self._project_root / "assets" / relative_asset_path))



