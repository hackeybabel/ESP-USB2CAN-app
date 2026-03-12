"""
Main window: port/baud selection, Connect/Disconnect, CAN log table, Send frame panel, status bar.
"""

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
)
from PyQt6.QtCore import Qt

from .bridge import Bridge, list_ports
from .can_log import CANLogView
from .send_frame import SendFramePanel
from .protocol import BAUD_INDEX_TO_RATE


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("ESP-USB2CAN app")
        self.resize(900, 600)

        self._bridge = Bridge(self)
        self._bridge.ack_received.connect(self._on_ack)
        self._bridge.frame_received.connect(self._on_frame)
        self._bridge.error.connect(self._on_error)

        central = QWidget()
        layout = QVBoxLayout(central)

        # Toolbar row: port, baud, connect, disconnect, refresh, clear log, pause
        row = QHBoxLayout()
        row.addWidget(QLabel("Port:"))
        self.port_combo = QComboBox()
        self.port_combo.setMinimumWidth(180)
        row.addWidget(self.port_combo)

        row.addWidget(QLabel("CAN baud:"))
        self.baud_combo = QComboBox()
        for i, rate in enumerate(BAUD_INDEX_TO_RATE):
            self.baud_combo.addItem(f"{rate // 1000} kbit/s", i)
        self.baud_combo.setCurrentIndex(2)  # 500 kbit/s
        row.addWidget(self.baud_combo)

        self.loopback_cb = QCheckBox("Loopback")
        self.loopback_cb.setToolTip("Use TWAI self-test/self-reception mode for local CAN bring-up.")
        row.addWidget(self.loopback_cb)

        self.connect_btn = QPushButton("Connect")
        self.connect_btn.clicked.connect(self._on_connect)
        row.addWidget(self.connect_btn)

        self.disconnect_btn = QPushButton("Disconnect")
        self.disconnect_btn.clicked.connect(self._on_disconnect)
        self.disconnect_btn.setEnabled(False)
        row.addWidget(self.disconnect_btn)

        self.refresh_btn = QPushButton("Refresh ports")
        self.refresh_btn.clicked.connect(self._refresh_ports)
        row.addWidget(self.refresh_btn)

        row.addWidget(QWidget(), 1)

        self.clear_btn = QPushButton("Clear log")
        self.clear_btn.clicked.connect(self._on_clear_log)
        row.addWidget(self.clear_btn)

        self.pause_cb = QCheckBox("Pause log")
        self.pause_cb.stateChanged.connect(
            lambda s: self.can_log.set_paused(s == Qt.CheckState.Checked.value)
        )
        row.addWidget(self.pause_cb)

        layout.addLayout(row)

        # Content: log table + send panel
        splitter = QSplitter(Qt.Orientation.Horizontal)
        self.can_log = CANLogView()
        splitter.addWidget(self.can_log)
        self.send_panel = SendFramePanel(self)
        self.send_panel.send_requested.connect(self._on_send_frame)
        self.send_panel.set_send_enabled(False)
        splitter.addWidget(self.send_panel)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 0)
        layout.addWidget(splitter)

        self.setCentralWidget(central)

        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self.status.showMessage("Disconnected")

        self._refresh_ports()

    def _refresh_ports(self) -> None:
        self.port_combo.clear()
        for port, desc in list_ports():
            self.port_combo.addItem(f"{port} — {desc}", port)
        if self.port_combo.count():
            self.port_combo.setCurrentIndex(0)

    def _on_connect(self) -> None:
        port = self.port_combo.currentData()
        if not port:
            self.status.showMessage("No port selected")
            return
        if not self._bridge.connect(port):
            return
        self.connect_btn.setEnabled(False)
        self.disconnect_btn.setEnabled(True)
        self.port_combo.setEnabled(False)
        self.baud_combo.setEnabled(False)
        self.loopback_cb.setEnabled(False)
        self.status.showMessage("Connected, opening CAN…")
        idx = self.baud_combo.currentData()
        self._bridge.set_baud(idx)
        self._bridge.set_loopback(self.loopback_cb.isChecked())
        self._bridge.open_can()

    def _on_ack(self, ok: bool) -> None:
        if ok:
            self.status.showMessage("Connected, CAN ready")
            self.send_panel.set_send_enabled(True)
        else:
            self.status.showMessage("CAN open failed")
            self.send_panel.set_send_enabled(False)
            QMessageBox.warning(self, "USB2CAN", "Device returned error (ACK ERR). Check baud and bus.")

    def _on_frame(self, frame) -> None:
        self.can_log.append_rx(frame)

    def _on_send_frame(self, id: int, extended: bool, rtr: bool, dlc: int, data: bytes) -> None:
        from .protocol import CANFrame
        self._bridge.send_frame(id, extended, rtr, dlc, data)
        # Optionally add TX row to log
        pad = data + bytes(8 - len(data))
        frame = CANFrame(id=id, extended=extended, rtr=rtr, dlc=dlc, data=pad[:8])
        self.can_log.append_tx(frame)

    def _on_disconnect(self) -> None:
        self._bridge.close_can()
        self._bridge.disconnect()
        self.send_panel.set_send_enabled(False)
        self.connect_btn.setEnabled(True)
        self.disconnect_btn.setEnabled(False)
        self.port_combo.setEnabled(True)
        self.baud_combo.setEnabled(True)
        self.loopback_cb.setEnabled(True)
        self.status.showMessage("Disconnected")

    def _on_error(self, msg: str) -> None:
        self.status.showMessage(f"Error: {msg}")
        QMessageBox.warning(self, "USB2CAN", msg)
        if self._bridge.is_connected():
            self._on_disconnect()

    def _on_clear_log(self) -> None:
        self.can_log.clear_log()

    def closeEvent(self, event) -> None:
        if self._bridge.is_connected():
            self._bridge.disconnect()
        event.accept()
