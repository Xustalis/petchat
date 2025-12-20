"""
UI Theme definitions complying with WCAG 2.1 AA and Modern UI standards.
"""
from PyQt6.QtGui import QColor

class Theme:
    """Application Theme Colors and Metrics"""
    
    # --- Colors ---
    # Primary Palette
    PRIMARY = "#2563eb"        # Blue 600 - Good contrast on white
    PRIMARY_HOVER = "#1d4ed8"  # Blue 700
    PRIMARY_TEXT = "#ffffff"   # White text on primary
    
    # Secondary/Accent
    SECONDARY = "#4b5563"      # Gray 600
    ACCENT = "#8b5cf6"         # Violet 500
    
    # Backgrounds
    BG_MAIN = "#f3f4f6"        # Gray 100 - Main app background
    BG_WHITE = "#ffffff"       # White - Cards/Panels
    BG_HOVER = "#f9fafb"       # Gray 50
    BG_SELECTED = "#e5e7eb"    # Gray 200
    
    # Text Colors (WCAG compliant)
    TEXT_PRIMARY = "#111827"   # Gray 900 - High contrast text
    TEXT_SECONDARY = "#4b5563" # Gray 600 - Secondary text (check contrast!)
    TEXT_DISABLED = "#9ca3af"  # Gray 400
    
    # Status Colors
    SUCCESS = "#059669"        # Emerald 600
    WARNING = "#d97706"        # Amber 600
    ERROR = "#dc2626"          # Red 600
    
    # --- Metrics (8px Grid) ---
    SPACING_XS = 4
    SPACING_SM = 8
    SPACING_MD = 16
    SPACING_LG = 24
    SPACING_XL = 32
    
    RADIUS_SM = 4
    RADIUS_MD = 8
    RADIUS_LG = 12
    
    # --- Typography ---
    FONT_SIZE_SM = 12
    FONT_SIZE_MD = 14
    FONT_SIZE_LG = 16
    FONT_SIZE_XL = 20
    
    @staticmethod
    def get_stylesheet():
        """Global application stylesheet"""
        return f"""
            QWidget {{
                color: {Theme.TEXT_PRIMARY};
                font-family: 'Segoe UI', system-ui, sans-serif;
            }}
            
            QMainWindow {{
                background-color: {Theme.BG_MAIN};
            }}
            
            /* Buttons */
            QPushButton {{
                background-color: {Theme.PRIMARY};
                color: {Theme.PRIMARY_TEXT};
                border: none;
                border-radius: {Theme.RADIUS_MD}px;
                padding: {Theme.SPACING_SM}px {Theme.SPACING_MD}px;
                font-size: {Theme.FONT_SIZE_MD}px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: {Theme.PRIMARY_HOVER};
            }}
            QPushButton:disabled {{
                background-color: {Theme.TEXT_DISABLED};
            }}
            
            /* Inputs */
            QLineEdit, QTextEdit {{
                background-color: {Theme.BG_WHITE};
                border: 1px solid #d1d5db;
                border-radius: {Theme.RADIUS_MD}px;
                padding: {Theme.SPACING_SM}px;
                font-size: {Theme.FONT_SIZE_MD}px;
                color: {Theme.TEXT_PRIMARY};
            }}
            QLineEdit:focus, QTextEdit:focus {{
                border: 2px solid {Theme.PRIMARY};
            }}
            
            /* Scrollbars */
            QScrollBar:vertical {{
                border: none;
                background: {Theme.BG_MAIN};
                width: 10px;
                margin: 0px 0px 0px 0px;
            }}
            QScrollBar::handle:vertical {{
                background: #d1d5db;
                min-height: 20px;
                border-radius: 5px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: #9ca3af;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                background: none;
            }}
        """
