#!/usr/bin/env python3
"""Entry script for PyInstaller: ensures src is on path then runs the GUI."""

import sys
from pathlib import Path

src = Path(__file__).resolve().parent / "src"
if str(src) not in sys.path:
    sys.path.insert(0, str(src))

from usb2can_gui.__main__ import main

if __name__ == "__main__":
    main()
