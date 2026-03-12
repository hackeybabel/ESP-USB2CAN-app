"""
Serial bridge to USB2CAN device: open/close port, send commands, RX thread with Qt signals.
"""

import serial
import serial.tools.list_ports
from PyQt6.QtCore import QObject, QThread, pyqtSignal

from .protocol import (
    ACK_ERR,
    ACK_OK,
    CANFrame,
    build_close,
    build_open,
    build_set_baud,
    build_set_mode,
    build_tx_frame,
    parse_rx_frame,
    ProtocolParser,
    MSG_ACK,
    MSG_RX_FRAME,
)


# Serial port baud rate for USB link (CDC); CAN bitrate is set via CMD_SET_BAUD
SERIAL_BAUD = 921600


def list_ports() -> list[tuple[str, str]]:
    """Return list of (port, description) for combo box."""
    return [(p.device, p.description or p.device) for p in serial.tools.list_ports.comports()]


class RxThread(QThread):
    """Thread that reads from serial and emits parsed messages via signals."""

    ack_received = pyqtSignal(bool)  # True = OK, False = ERR
    frame_received = pyqtSignal(object)  # CANFrame
    error = pyqtSignal(str)

    def __init__(self, ser: serial.Serial, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._ser = ser
        self._parser = ProtocolParser()
        self._stop = False

    def stop(self) -> None:
        self._stop = True

    def run(self) -> None:
        try:
            while not self._stop and self._ser.is_open:
                try:
                    data = self._ser.read(self._ser.in_waiting or 1)
                except (OSError, serial.SerialException) as e:
                    self.error.emit(str(e))
                    break
                if not data:
                    self.msleep(1)
                    continue
                for msg_type, payload in self._parser.feed(data):
                    if msg_type == MSG_ACK and payload and len(payload) >= 1:
                        self.ack_received.emit(payload[0] == ACK_OK)
                    elif msg_type == MSG_RX_FRAME and payload:
                        try:
                            frame = parse_rx_frame(payload)
                            self.frame_received.emit(frame)
                        except ValueError:
                            pass
        except Exception as e:
            self.error.emit(str(e))
        finally:
            self._parser.reset()


class Bridge(QObject):
    """
    Connects to USB2CAN device over serial. Sends commands and exposes
    ack_received / frame_received signals. Run connect() then set_baud() (optional)
    then open_can(); use send_frame() when CAN is open. Call disconnect() when done.
    """

    ack_received = pyqtSignal(bool)  # True = OK, False = ERR
    frame_received = pyqtSignal(object)  # CANFrame
    error = pyqtSignal(str)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._ser: serial.Serial | None = None
        self._rx_thread: RxThread | None = None
        self._can_open = False

    def connect(self, port: str) -> bool:
        """Open serial port and start RX thread. Emit error and return False on failure."""
        if self._ser is not None:
            self.error.emit("Already connected")
            return False
        try:
            self._ser = serial.Serial(
                port=port,
                baudrate=SERIAL_BAUD,
                timeout=0.01,
                write_timeout=1.0,
            )
        except Exception as e:
            self.error.emit(str(e))
            return False
        self._rx_thread = RxThread(self._ser, self)
        self._rx_thread.ack_received.connect(self.ack_received.emit)
        self._rx_thread.frame_received.connect(self.frame_received.emit)
        self._rx_thread.error.connect(self.error.emit)
        self._rx_thread.start()
        return True

    def disconnect(self) -> None:
        """Close CAN if open, stop RX thread, close serial."""
        self._can_open = False
        if self._rx_thread is not None:
            self._rx_thread.stop()
            self._rx_thread.wait(2000)
            self._rx_thread = None
        if self._ser is not None:
            try:
                self._ser.close()
            except Exception:
                pass
            self._ser = None

    def is_connected(self) -> bool:
        return self._ser is not None and self._ser.is_open

    def is_can_open(self) -> bool:
        return self._can_open

    def set_baud(self, index: int) -> None:
        """Send CMD_SET_BAUD. Only valid when CAN is closed."""
        if self._ser is None or not self._ser.is_open:
            return
        try:
            self._ser.write(build_set_baud(index))
            self._ser.flush()
        except Exception as e:
            self.error.emit(str(e))

    def set_loopback(self, loopback: bool) -> None:
        """Send CMD_SET_MODE. Only valid when CAN is closed."""
        if self._ser is None or not self._ser.is_open:
            return
        try:
            self._ser.write(build_set_mode(loopback))
            self._ser.flush()
        except Exception as e:
            self.error.emit(str(e))

    def open_can(self) -> None:
        """Send CMD_OPEN. Expect ack_received shortly after."""
        if self._ser is None or not self._ser.is_open:
            return
        try:
            self._ser.write(build_open())
            self._ser.flush()
            self._can_open = True
        except Exception as e:
            self.error.emit(str(e))

    def close_can(self) -> None:
        """Send CMD_CLOSE and mark CAN as closed after send."""
        if self._ser is None or not self._ser.is_open:
            return
        try:
            self._ser.write(build_close())
            self._ser.flush()
            self._can_open = False
        except Exception as e:
            self.error.emit(str(e))

    def send_frame(
        self,
        id: int,
        extended: bool,
        rtr: bool,
        dlc: int,
        data: bytes,
    ) -> None:
        """Send one CAN frame (CMD_TX_FRAME). No ACK from device."""
        if self._ser is None or not self._ser.is_open:
            return
        try:
            payload = build_tx_frame(id, extended, rtr, dlc, data)
            self._ser.write(payload)
            self._ser.flush()
        except Exception as e:
            self.error.emit(str(e))
