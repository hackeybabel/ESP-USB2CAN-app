# Copyright (c) 2026 Hemant Babel
# SPDX-License-Identifier: GPL-3.0-only
"""
CAN bus load calculation from RX/TX frame stream.
Uses a sliding time window; load = (bits in window) / (bitrate * window_sec).
"""

import time
from collections import deque
from dataclasses import dataclass

from .protocol import CANFrame, BAUD_INDEX_TO_RATE


def bits_per_frame(frame: CANFrame) -> int:
    """
    Nominal bit count for one CAN frame on the wire (without bit stuffing).
    Standard: 46 + 8*DLC; Extended: 64 + 8*DLC.
    """
    if frame.extended:
        return 64 + 8 * frame.dlc
    return 46 + 8 * frame.dlc


@dataclass
class BusLoadSnapshot:
    """Current bus load and related metrics."""
    load_percent: float
    bits_per_sec: float
    frames_per_sec: float
    bitrate_bps: int


class BusLoadCalculator:
    """
    Tracks frames in a sliding time window and computes bus load.
    Call add_frame() for each RX and TX frame; get_snapshot() returns current load.
    """

    def __init__(self, baud_index: int = 2, window_sec: float = 1.0) -> None:
        self._baud_index = baud_index
        self._window_sec = window_sec
        # (timestamp, bits)
        self._events: deque[tuple[float, int]] = deque()
        self._max_events = 100_000

    def set_baud_index(self, index: int) -> None:
        self._baud_index = max(0, min(index, len(BAUD_INDEX_TO_RATE) - 1))

    def add_frame(self, frame: CANFrame, ts: float | None = None) -> None:
        if ts is None:
            ts = time.time()
        bits = bits_per_frame(frame)
        self._events.append((ts, bits))
        while len(self._events) > self._max_events:
            self._events.popleft()

    def get_snapshot(self) -> BusLoadSnapshot:
        """Compute load over the last window_sec. Prune old events."""
        now = time.time()
        cutoff = now - self._window_sec
        total_bits = 0
        count = 0
        while self._events and self._events[0][0] < cutoff:
            self._events.popleft()
        for ts, bits in self._events:
            total_bits += bits
            count += 1
        bitrate_bps = BAUD_INDEX_TO_RATE[self._baud_index]
        bits_per_sec = total_bits / self._window_sec if self._window_sec > 0 else 0.0
        frames_per_sec = count / self._window_sec if self._window_sec > 0 else 0.0
        load_percent = (bits_per_sec / bitrate_bps * 100.0) if bitrate_bps > 0 else 0.0
        return BusLoadSnapshot(
            load_percent=min(100.0, load_percent),
            bits_per_sec=bits_per_sec,
            frames_per_sec=frames_per_sec,
            bitrate_bps=bitrate_bps,
        )

    def reset(self) -> None:
        self._events.clear()


