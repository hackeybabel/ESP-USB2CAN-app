#!/usr/bin/env python3
# Copyright (c) 2026 Hemant Babel
# SPDX-License-Identifier: GPL-3.0-only
"""Launch USB2CAN GUI. Run from host_app dir or with PYTHONPATH including src."""

import sys
from pathlib import Path

# Ensure src is on path when running main.py from host_app
src = Path(__file__).resolve().parent / "src"
if str(src) not in sys.path:
    sys.path.insert(0, str(src))

from usb2can_gui.__main__ import main

if __name__ == "__main__":
    main()


