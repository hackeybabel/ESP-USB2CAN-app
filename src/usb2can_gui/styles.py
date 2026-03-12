# Copyright (c) 2026 Hemant Babel
# SPDX-License-Identifier: GPL-3.0-only
"""
Material Design-inspired light theme for ESP-USB2CAN app.
Light surfaces, subtle elevation, primary blue accent, clean typography.
"""

# Material light palette
BACKGROUND = "#EEF2F7"
SURFACE = "#FFFFFF"
SURFACE_VARIANT = "#F7F9FC"
PRIMARY = "#1976D2"          # Blue 700
PRIMARY_HOVER = "#1565C0"    # Blue 800
PRIMARY_CONTAINER = "#BBDEFB"  # Blue 100
OUTLINE = "#C7CFD9"
OUTLINE_VARIANT = "#DAE1EA"
ON_SURFACE = "#1F2733"
ON_SURFACE_VARIANT = "#5F6B7A"
ON_PRIMARY = "#FFFFFF"
ON_PRIMARY_CONTAINER = "#0D47A1"
ERROR = "#B00020"
SUCCESS = "#2E7D32"
SHADOW = "rgba(0, 0, 0, 0.08)"
SHADOW_MED = "rgba(0, 0, 0, 0.12)"

# Spacing (8dp grid)
SPACING_XS = 4
SPACING_SM = 8
SPACING_MD = 16
SPACING_LG = 24
RADIUS_SM = 4
RADIUS_MD = 8
RADIUS_LG = 12


def get_stylesheet() -> str:
    return f"""
    /* Global */
    QWidget {{
        background-color: {BACKGROUND};
        color: {ON_SURFACE};
        font-family: "Segoe UI", "SF Pro Display", system-ui, sans-serif;
        font-size: 14px;
    }}

    QLabel {{
        background-color: transparent;
    }}

    /* Cards (elevated surface) */
    QFrame#card {{
        background-color: {SURFACE};
        border: 1px solid {OUTLINE_VARIANT};
        border-radius: {RADIUS_MD}px;
        padding: 8px;
    }}

    QFrame#cardCompact {{
        background-color: {SURFACE};
        border: 1px solid {OUTLINE_VARIANT};
        border-radius: {RADIUS_MD}px;
        padding: 0;
    }}

    QLabel#sectionTitle {{
        font-size: 12px;
        font-weight: 600;
    }}

    QLabel#subtleText {{
        color: {ON_SURFACE_VARIANT};
        font-size: 12px;
    }}

    QLabel#formError {{
        color: {ERROR};
        font-size: 12px;
        min-height: 16px;
    }}

    QLabel#warningText {{
        color: {ERROR};
        font-size: 12px;
        font-weight: 600;
    }}

    QLabel#emptyState {{
        color: {ON_SURFACE_VARIANT};
        font-size: 13px;
    }}

    QLabel#connectionState {{
        border-radius: 12px;
        padding: 5px 12px;
        font-size: 12px;
        font-weight: 600;
        min-height: 24px;
    }}
    QLabel#connectionState[state="disconnected"] {{
        color: {ON_SURFACE_VARIANT};
        background-color: {OUTLINE_VARIANT};
    }}
    QLabel#connectionState[state="connecting"] {{
        color: {ON_PRIMARY_CONTAINER};
        background-color: {PRIMARY_CONTAINER};
    }}
    QLabel#connectionState[state="ready"] {{
        color: {SUCCESS};
        background-color: #E8F5E9;
    }}
    QLabel#connectionState[state="error"] {{
        color: {ERROR};
        background-color: #FDECEC;
    }}

    /* Primary button (filled) */
    QPushButton#primaryBtn {{
        background-color: {PRIMARY};
        color: {ON_PRIMARY};
        border: none;
        border-radius: {RADIUS_SM}px;
        padding: 7px 16px;
        font-weight: 600;
        min-height: 32px;
    }}
    QPushButton#primaryBtn:hover {{
        background-color: {PRIMARY_HOVER};
    }}
    QPushButton#primaryBtn:pressed {{
        background-color: {PRIMARY_HOVER};
    }}
    QPushButton#primaryBtn:disabled {{
        background-color: {OUTLINE_VARIANT};
        color: {ON_SURFACE_VARIANT};
    }}

    /* Secondary / outlined button */
    QPushButton#secondaryBtn {{
        background-color: transparent;
        color: {PRIMARY};
        border: 1px solid {PRIMARY};
        border-radius: {RADIUS_SM}px;
        padding: 7px 14px;
        min-height: 32px;
    }}
    QPushButton#secondaryBtn:hover {{
        background-color: {PRIMARY_CONTAINER};
    }}
    QPushButton#secondaryBtn:pressed {{
        background-color: {OUTLINE_VARIANT};
    }}
    QPushButton#secondaryBtn:disabled {{
        border-color: {OUTLINE};
        color: {ON_SURFACE_VARIANT};
    }}

    /* Text button */
    QPushButton#textBtn {{
        background-color: transparent;
        color: {PRIMARY};
        border: none;
        border-radius: {RADIUS_SM}px;
        padding: 7px 10px;
        min-height: 32px;
    }}
    QPushButton#textBtn:hover {{
        background-color: {PRIMARY_CONTAINER};
    }}
    QPushButton#textBtn:pressed {{
        background-color: {OUTLINE_VARIANT};
    }}

    /* Default buttons (e.g. Send, Clear) */
    QPushButton {{
        background-color: {SURFACE};
        color: {ON_SURFACE};
        border: 1px solid {OUTLINE};
        border-radius: {RADIUS_SM}px;
        padding: 7px 12px;
        min-height: 32px;
    }}
    QPushButton:hover {{
        background-color: {SURFACE_VARIANT};
        border-color: {ON_SURFACE_VARIANT};
    }}
    QPushButton:pressed {{
        background-color: {OUTLINE_VARIANT};
    }}
    QPushButton:disabled {{
        background-color: #E7ECF2;
        color: #7B8795;
        border-color: #C8D1DC;
    }}

    /* ComboBox */
    QComboBox {{
        background-color: {SURFACE};
        color: {ON_SURFACE};
        border: 1px solid {OUTLINE};
        border-radius: {RADIUS_SM}px;
        padding: 6px 10px;
        min-height: 32px;
        min-width: 100px;
    }}
    QComboBox:hover {{
        border-color: {ON_SURFACE_VARIANT};
    }}
    QComboBox:focus {{
        border-color: {PRIMARY};
    }}
    QComboBox::drop-down {{
        subcontrol-origin: padding;
        subcontrol-position: right center;
        width: 22px;
        border: none;
        background: {OUTLINE_VARIANT};
        border-radius: 0 {RADIUS_SM}px {RADIUS_SM}px 0;
    }}
    QComboBox:disabled {{
        background-color: #E7ECF2;
        color: #7B8795;
        border-color: #C8D1DC;
    }}
    QComboBox QAbstractItemView {{
        background-color: {SURFACE};
        border: 1px solid {OUTLINE};
        border-radius: {RADIUS_SM}px;
        padding: 4px;
        selection-background-color: {PRIMARY_CONTAINER};
        selection-color: {ON_SURFACE};
    }}

    /* LineEdit */
    QLineEdit {{
        background-color: {SURFACE};
        color: {ON_SURFACE};
        border: 1px solid {OUTLINE};
        border-radius: {RADIUS_SM}px;
        padding: 6px 10px;
        min-height: 32px;
    }}
    QLineEdit:hover {{
        border-color: {ON_SURFACE_VARIANT};
    }}
    QLineEdit:focus {{
        border-color: {PRIMARY};
    }}
    QLineEdit[state="error"] {{
        border-color: {ERROR};
        background-color: #FFF5F6;
    }}
    QLineEdit:disabled {{
        background-color: #EEF2F6;
        color: #7B8795;
        border-color: #C8D1DC;
    }}
    QLineEdit::placeholder {{
        color: {ON_SURFACE_VARIANT};
    }}

    /* SpinBox */
    QSpinBox {{
        background-color: {SURFACE};
        color: {ON_SURFACE};
        border: 1px solid {OUTLINE};
        border-radius: {RADIUS_SM}px;
        padding: 6px 10px;
        min-height: 32px;
    }}
    QSpinBox:hover {{
        border-color: {ON_SURFACE_VARIANT};
    }}
    QSpinBox:focus {{
        border-color: {PRIMARY};
    }}
    QSpinBox[state="locked"] {{
        background-color: {SURFACE_VARIANT};
        color: {ON_SURFACE_VARIANT};
    }}
    QSpinBox:disabled {{
        background-color: #EEF2F6;
        color: #7B8795;
        border-color: #C8D1DC;
    }}

    /* CheckBox */
    QCheckBox {{
        spacing: 6px;
        color: {ON_SURFACE};
        padding: 4px 0;
        background-color: transparent;
    }}
    QCheckBox::indicator {{
        width: 18px;
        height: 18px;
        border-radius: 3px;
        border: 2px solid {OUTLINE};
        background-color: {SURFACE};
    }}
    QCheckBox::indicator:hover {{
        border-color: {PRIMARY};
    }}
    QCheckBox::indicator:checked {{
        background-color: {PRIMARY};
        border-color: {PRIMARY};
    }}

    /* ProgressBar */
    QProgressBar {{
        background-color: {OUTLINE_VARIANT};
        border: none;
        border-radius: 6px;
        text-align: center;
        min-height: 16px;
        max-height: 16px;
        font-size: 12px;
    }}
    QProgressBar::chunk {{
        background-color: {PRIMARY};
        border-radius: 6px;
    }}

    /* Table (CAN log) */
    QTableView {{
        background-color: {SURFACE};
        border: 1px solid {OUTLINE_VARIANT};
        border-radius: {RADIUS_SM}px;
        gridline-color: {OUTLINE_VARIANT};
        selection-background-color: #DDEBFA;
        selection-color: #0E2438;
    }}
    QTableView::item {{
        padding: 5px 8px;
    }}
    QTableView::item:alternate {{
        background-color: {SURFACE_VARIANT};
    }}
    QTableView::item:selected {{
        background-color: #DDEBFA;
        color: #0E2438;
    }}
    QTableView::item:selected:active {{
        background-color: #D0E3F8;
        color: #0E2438;
    }}
    QTableView::item:selected:!active {{
        background-color: #E4EEF9;
        color: #1C3349;
    }}
    QHeaderView::section {{
        background-color: {SURFACE_VARIANT};
        color: {ON_SURFACE_VARIANT};
        padding: 7px 8px;
        border: none;
        border-bottom: 2px solid {OUTLINE};
        font-weight: 600;
    }}

    /* Status bar */
    QStatusBar {{
        background-color: {SURFACE};
        color: {ON_SURFACE_VARIANT};
        border-top: 1px solid {OUTLINE_VARIANT};
        padding: 4px 8px;
        font-size: 13px;
    }}

    /* Labels in cards */
    QFrame#card QLabel,
    QFrame#cardCompact QLabel {{
        color: {ON_SURFACE};
    }}

    /* Splitter */
    QSplitter::handle {{
        background-color: {OUTLINE_VARIANT};
        width: 6px;
        height: 6px;
    }}
    QSplitter::handle:hover {{
        background-color: {OUTLINE};
    }}
    """



