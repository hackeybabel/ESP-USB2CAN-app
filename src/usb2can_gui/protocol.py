"""
Binary protocol for USB2CAN (ESP32-C3) bridge.
All multi-byte values are little-endian. Matches main/usb2can_bridge.c.
"""

import struct
from dataclasses import dataclass
from typing import Optional

# Commands: host -> device
CMD_OPEN = 0x01
CMD_CLOSE = 0x02
CMD_SET_BAUD = 0x03
CMD_SET_MODE = 0x04
CMD_TX_FRAME = 0x10

# Messages: device -> host
MSG_ACK = 0x00
MSG_RX_FRAME = 0x20

# ACK status
ACK_OK = 0x00
ACK_ERR = 0x01

# Frame flags (1 byte)
FRAME_FLAG_EXT = 1 << 0
FRAME_FLAG_RTR = 1 << 1

# Frame payload: id(4) + flags(1) + dlc(1) + data(8) = 14 bytes
FRAME_PAYLOAD_LEN = 14

# Baud index -> bitrate (kbit/s)
BAUD_INDEX_TO_RATE = (125_000, 250_000, 500_000, 1_000_000)
BAUD_INDEX_MAX = len(BAUD_INDEX_TO_RATE) - 1

# Controller mode values for CMD_SET_MODE
MODE_NORMAL = 0x00
MODE_LOOPBACK = 0x01


@dataclass
class CANFrame:
    """Decoded CAN frame (RX or TX)."""
    id: int
    extended: bool
    rtr: bool
    dlc: int
    data: bytes  # length 8, only first `dlc` bytes meaningful for data frames

    def data_hex(self) -> str:
        n = min(self.dlc, len(self.data))
        return self.data[:n].hex(" ").upper() if n else ""

    def id_hex(self) -> str:
        w = 8 if self.extended else 3
        return f"{self.id:0{w}X}"


def build_open() -> bytes:
    return bytes([CMD_OPEN])


def build_close() -> bytes:
    return bytes([CMD_CLOSE])


def build_set_baud(index: int) -> bytes:
    if not 0 <= index <= BAUD_INDEX_MAX:
        raise ValueError(f"Baud index must be 0..{BAUD_INDEX_MAX}")
    return bytes([CMD_SET_BAUD, index])


def build_set_mode(loopback: bool) -> bytes:
    return bytes([CMD_SET_MODE, MODE_LOOPBACK if loopback else MODE_NORMAL])


def build_tx_frame(
    id: int,
    extended: bool,
    rtr: bool,
    dlc: int,
    data: bytes,
) -> bytes:
    if not 0 <= dlc <= 8:
        raise ValueError("DLC must be 0..8")
    if len(data) < 8:
        data = data + bytes(8 - len(data))
    data = data[:8]
    flags = 0
    if extended:
        flags |= FRAME_FLAG_EXT
    if rtr:
        flags |= FRAME_FLAG_RTR
    # id: 4 bytes LE
    payload = struct.pack("<IBB", id & 0xFFFFFFFF, flags, dlc) + data
    return bytes([CMD_TX_FRAME]) + payload


def parse_rx_frame(payload: bytes) -> CANFrame:
    """Parse 14-byte frame payload into CANFrame. Raises ValueError if len != 14."""
    if len(payload) != FRAME_PAYLOAD_LEN:
        raise ValueError(f"Expected {FRAME_PAYLOAD_LEN} bytes, got {len(payload)}")
    id_, flags, dlc = struct.unpack("<IBB", payload[:6])
    data = payload[6:14]
    extended = bool(flags & FRAME_FLAG_EXT)
    rtr = bool(flags & FRAME_FLAG_RTR)
    return CANFrame(id=id_, extended=extended, rtr=rtr, dlc=dlc, data=data)


class ProtocolParser:
    """
    Stateful parser for the device -> host stream.
    Handles partial reads; yields (msg_type, payload).
    """

    def __init__(self) -> None:
        self._buffer = bytearray()
        self._msg_type: Optional[int] = None  # MSG_ACK or MSG_RX_FRAME after first byte
        self._expect_len: Optional[int] = None  # payload length to read

    def feed(self, data: bytes) -> list[tuple[int, bytes]]:
        """
        Feed bytes from the serial port.
        Returns list of (msg_type, payload):
          - (MSG_ACK, bytes([status]))
          - (MSG_RX_FRAME, 14-byte payload)
        """
        self._buffer.extend(data)
        out: list[tuple[int, bytes]] = []
        while True:
            if self._expect_len is None:
                if len(self._buffer) < 1:
                    break
                first = self._buffer.pop(0)
                if first == MSG_ACK:
                    self._msg_type = MSG_ACK
                    self._expect_len = 1
                elif first == MSG_RX_FRAME:
                    self._msg_type = MSG_RX_FRAME
                    self._expect_len = FRAME_PAYLOAD_LEN
                else:
                    continue
            if len(self._buffer) < self._expect_len:
                break
            payload = bytes(self._buffer[: self._expect_len])
            del self._buffer[: self._expect_len]
            out.append((self._msg_type, payload))
            self._msg_type = None
            self._expect_len = None
        return out

    def reset(self) -> None:
        self._buffer.clear()
        self._msg_type = None
        self._expect_len = None
