"""
UI Theme definitions complying with WCAG 2.1 AA and Modern UI standards.
"""
from PyQt6.QtGui import QColor


class Theme:
    """Application Theme Colors and Metrics"""

    # Material Design 3 Light Code Palette
    PRIMARY = "#6750A4"       # M3 Purple
    PRIMARY_HOVER = "#7F67BE" 
    PRIMARY_TEXT = "#FFFFFF"

    SECONDARY = "#625B71"
    ACCENT = "#7D5260"

    # Backgrounds - Light Mode
    BG_MAIN = "#FFFBFE"       # Main window background
    BG_ELEVATED = "#F7F2FA"   # Sidebars / Cards (Surface 1)
    BG_SURFACE = "#ECE6F0"    # Input fields / secondary (M3 Surface Container High)
    BG_MUTED = "#F3EDF7"      # Generic muted background (Surface 2)
    BG_BORDER = "#CAC4D0"     # Darker border (M3 Outline) for better contrast
    BG_HOVER = "#E8DEF8"      # Hover state
    BG_SELECTED = "#E8DEF8"   # Selected state

    # Text Colors - High Contrast
    TEXT_PRIMARY = "#1C1B1F"
    TEXT_SECONDARY = "#49454F"
    TEXT_DISABLED = "#9E9E9E"

    SUCCESS = "#469F66"       # M3 Green
    WARNING = "#E5B94E"       # M3 Yellow/Amber
    ERROR = "#BA1A1A"         # M3 Red

    SPACING_XS = 4
    SPACING_SM = 8
    SPACING_MD = 16
    SPACING_LG = 24
    SPACING_XL = 32

    RADIUS_SM = 8
    RADIUS_MD = 12
    RADIUS_LG = 20

    FONT_SIZE_SM = 12
    FONT_SIZE_MD = 14
    FONT_SIZE_LG = 16
    FONT_SIZE_XL = 20

    @staticmethod
    @staticmethod
    @staticmethod
    def get_stylesheet():
        return f"""
            /* Global Reset & Base Defaults */
            QMainWindow {{
                background-color: {Theme.BG_MAIN};
            }}
            QDialog {{
                background-color: {Theme.BG_MAIN};
            }}
            QWidget#central, QWidget#sidebar {{
                background-color: {Theme.BG_MAIN};
            }}

            /* Typography & Colors */
            QLabel {{
                color: {Theme.TEXT_PRIMARY};
                font-family: 'Segoe UI', 'Microsoft YaHei', 'Roboto', sans-serif;
            }}
            
            /* Splitter - Make handle distinct but not ugly black */
            QSplitter::handle {{
                background-color: {Theme.BG_BORDER};
                width: 1px; /* Thin separator line */
            }}

            /* Menu Bar & Menus */
            QMenuBar {{
                background-color: {Theme.BG_ELEVATED};
                color: {Theme.TEXT_PRIMARY};
                border-bottom: 1px solid {Theme.BG_BORDER};
                padding: 4px;
            }}
            QMenuBar::item {{
                padding: 6px 12px;
                background: transparent;
                border-radius: {Theme.RADIUS_SM}px;
                margin: 0 4px;
                color: {Theme.TEXT_PRIMARY};
            }}
            QMenuBar::item:selected {{
                background-color: {Theme.BG_HOVER};
            }}

            QMenu {{
                background-color: {Theme.BG_ELEVATED};
                color: {Theme.TEXT_PRIMARY};
                border: 1px solid {Theme.BG_BORDER};
                border-radius: {Theme.RADIUS_MD}px;
                padding: 4px;
            }}
            QMenu::item {{
                padding: 8px 24px 8px 12px;
                border-radius: {Theme.RADIUS_SM}px;
                margin: 0 4px;
            }}
            QMenu::item:selected {{
                background-color: {Theme.BG_HOVER};
                color: {Theme.TEXT_PRIMARY};
            }}
            QMenu::separator {{
                height: 1px;
                background: {Theme.BG_BORDER};
                margin: 4px 0;
            }}

            /* Buttons */
            QPushButton {{
                background-color: {Theme.PRIMARY};
                color: {Theme.PRIMARY_TEXT};
                border: none;
                border-radius: 20px;
                padding: 8px 24px;
                font-size: {Theme.FONT_SIZE_MD}px;
                font-weight: 600;
                font-family: 'Segoe UI', sans-serif;
            }}
            QPushButton:hover {{
                background-color: {Theme.PRIMARY_HOVER};
            }}
            QPushButton:pressed {{
                background-color: {Theme.PRIMARY};
                padding-top: 9px;
            }}
            QPushButton:disabled {{
                background-color: {Theme.BG_BORDER};
                color: {Theme.TEXT_DISABLED};
            }}

            /* Inputs */
            QLineEdit, QTextEdit, QComboBox {{
                background-color: {Theme.BG_SURFACE};
                border: 1px solid {Theme.BG_BORDER};
                border-radius: {Theme.RADIUS_MD}px;
                padding: 10px 12px;
                font-size: {Theme.FONT_SIZE_MD}px;
                color: {Theme.TEXT_PRIMARY};
                selection-background-color: {Theme.PRIMARY};
                selection-color: {Theme.PRIMARY_TEXT};
            }}
            QLineEdit:focus, QTextEdit:focus, QComboBox:focus {{
                border: 2px solid {Theme.PRIMARY};
                background-color: {Theme.BG_MAIN};
            }}
            QLineEdit::placeholder, QTextEdit::placeholder {{
                color: {Theme.TEXT_SECONDARY};
            }}

            /* Tabs */
            QTabWidget::pane {{
                border: none;
                background: {Theme.BG_MAIN};
            }}
            QTabBar::tab {{
                background: transparent;
                color: {Theme.TEXT_SECONDARY};
                padding: 10px 16px;
                margin: 0 4px;
                border-bottom: 2px solid transparent;
                font-weight: 500;
            }}
            QTabBar::tab:selected {{
                color: {Theme.PRIMARY};
                border-bottom: 2px solid {Theme.PRIMARY};
            }}
            QTabBar::tab:hover:!selected {{
                background-color: {Theme.BG_HOVER};
                border-radius: {Theme.RADIUS_SM}px;
            }}

            /* Lists */
            QListWidget {{
                background-color: transparent;
                border: none;
                outline: none;
            }}
            QListWidget::item {{
                background: transparent;
                border: none;
                padding: 0px;
                margin: 0px;
            }}
            QListWidget::item:selected {{
                background-color: transparent;
            }}
            QListWidget::item:hover:!selected {{
                background-color: transparent;
            }}

            /* Checkbox & Radio */
            QRadioButton, QCheckBox {{
                spacing: 8px;
                color: {Theme.TEXT_PRIMARY};
            }}
            QRadioButton::indicator, QCheckBox::indicator {{
                width: 18px;
                height: 18px;
                border: 2px solid {Theme.SECONDARY};
                background: {Theme.BG_MAIN};
                border-radius: 4px;
            }}
            QRadioButton::indicator {{
                border-radius: 10px;
            }}
            QRadioButton::indicator:checked {{
                background-color: {Theme.PRIMARY};
                border: 4px solid {Theme.BG_MAIN}; 
                outline: 1px solid {Theme.PRIMARY}; 
            }}
            QCheckBox::indicator:checked {{
                background-color: {Theme.PRIMARY};
                border: 2px solid {Theme.PRIMARY};
            }}

            /* Scrollbars */
            QScrollBar:vertical {{
                border: none;
                background: transparent;
                width: 8px;
                margin: 0;
            }}
            QScrollBar::handle:vertical {{
                background: {Theme.BG_BORDER};
                min-height: 24px;
                border-radius: 4px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {Theme.TEXT_DISABLED};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
                background: none;
            }}
        """
