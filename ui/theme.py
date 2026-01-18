"""
UI Theme definitions complying with WCAG 2.1 AA and Modern UI standards.
"""
from PyQt6.QtGui import QColor


class ThemeManager:
    """Manages theme switching and current theme state"""
    _current_theme = "light"
    _zoom_level = 100  # Percentage
    
    @classmethod
    def get_current_theme(cls):
        return cls._current_theme
    
    @classmethod
    def set_theme(cls, theme_name: str):
        cls._current_theme = theme_name
    
    @classmethod
    def get_zoom_level(cls):
        return cls._zoom_level
    
    @classmethod
    def set_zoom_level(cls, level: int):
        cls._zoom_level = max(50, min(200, level))
    
    @classmethod
    def get_theme_class(cls):
        """Returns the appropriate theme class based on current theme"""
        if cls._current_theme == "dark":
            return DarkTheme
        return Theme


class Theme:
    """Application Theme Colors and Metrics"""

    # Material Design 3 Light Code Palette
    PRIMARY = "#6750A4"       # M3 Purple
    PRIMARY_HOVER = "#7F67BE" 
    PRIMARY_TEXT = "#FFFFFF"

    SECONDARY = "#625B71"
    ACCENT = "#7D5260"

    # Backgrounds - Light Mode (Modern 3-Column Layout)
    BG_MAIN = "#FFFBFE"       # Main window background
    BG_ELEVATED = "#F7F2FA"   # Cards (Surface 1)
    BG_SURFACE = "#ECE6F0"    # Input fields / secondary (M3 Surface Container High)
    BG_MUTED = "#F3EDF7"      # Generic muted background (Surface 2)
    BG_BORDER = "#CAC4D0"     # Darker border (M3 Outline) for better contrast
    BG_HOVER = "#E8DEF8"      # Hover state
    BG_SELECTED = "#E8DEF8"   # Selected state
    
    # Modern Layout - Visual Hierarchy
    SIDEBAR_BG = "#F5F7FA"    # Cool grey-blue for sidebars
    CHAT_BG = "#FFFFFF"       # Pure white for center chat area
    CHAT_PATTERN = "#E8E8E8"  # Dot grid pattern color
    
    # Gradient colors for user chat bubble
    BUBBLE_GRADIENT_START = "#7C3AED"  # Vibrant purple
    BUBBLE_GRADIENT_END = "#A855F7"    # Lighter purple
    BUBBLE_OTHER_BG = "#F0F0F0"        # Light grey for AI/other messages

    # Text Colors - High Contrast
    TEXT_PRIMARY = "#1C1B1F"
    TEXT_SECONDARY = "#49454F"
    TEXT_DISABLED = "#9E9E9E"

    # Suggestion Module Colors
    SUGGESTION_BG = "#F5F7FA"
    SUGGESTION_TEXT = "#1E293B"
    SUGGESTION_SHADOW_COLOR = (0, 0, 0, 13) # 0.05 alpha

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

    @classmethod
    def get_stylesheet(cls):
        # Calculate scaled sizes based on zoom level
        zoom = ThemeManager.get_zoom_level() / 100.0
        
        radius_sm = int(cls.RADIUS_SM * zoom)
        radius_md = int(cls.RADIUS_MD * zoom)
        
        fs_sm = int(cls.FONT_SIZE_SM * zoom)
        fs_md = int(cls.FONT_SIZE_MD * zoom)
        
        # Helper for 3D colors
        def darker(hex_color, factor=120):
            c = QColor(hex_color)
            return c.darker(factor).name()

        primary_shadow = darker(cls.PRIMARY)
        primary_hover_shadow = darker(cls.PRIMARY_HOVER)
        error_shadow = darker(cls.ERROR)
        
        return f"""
            /* Global Reset & Base Defaults */
            QMainWindow {{
                background-color: {cls.BG_MAIN};
            }}
            QDialog {{
                background-color: {cls.BG_MAIN};
            }}
            QWidget#central {{
                background-color: {cls.BG_MAIN};
            }}
            /* Left & Right sidebars - Cool grey-blue */
            QWidget#sidebar {{
                background-color: {cls.SIDEBAR_BG};
                border-right: 1px solid {cls.BG_BORDER};
            }}

            /* Typography & Colors */
            QLabel {{
                color: {cls.TEXT_PRIMARY};
                font-family: 'Segoe UI', 'Microsoft YaHei', 'Roboto', sans-serif;
            }}
            
            /* Splitter */
            QSplitter::handle {{
                background-color: {cls.BG_BORDER};
                width: 1px;
            }}

            /* Menu Bar & Menus */
            QMenuBar {{
                background-color: {cls.BG_ELEVATED};
                color: {cls.TEXT_PRIMARY};
                border-bottom: 1px solid {cls.BG_BORDER};
                padding: 4px;
            }}
            QMenuBar::item {{
                padding: 6px 12px;
                background: transparent;
                border-radius: {radius_sm}px;
                margin: 0 4px;
                color: {cls.TEXT_PRIMARY};
            }}
            QMenuBar::item:selected {{
                background-color: {cls.BG_HOVER};
            }}

            QMenu {{
                background-color: {cls.BG_ELEVATED};
                color: {cls.TEXT_PRIMARY};
                border: 1px solid {cls.BG_BORDER};
                border-radius: {radius_md}px;
                padding: 4px;
            }}
            QMenu::item {{
                padding: 8px 24px 8px 12px;
                border-radius: {radius_sm}px;
                margin: 0 4px;
                color: {cls.TEXT_PRIMARY};
            }}
            QMenu::item:selected {{
                background-color: {cls.BG_HOVER};
                color: {cls.TEXT_PRIMARY};
            }}
            QMenu::separator {{
                height: 1px;
                background: {cls.BG_BORDER};
                margin: 4px 0;
            }}

            /* Buttons - 3D Style */
            QPushButton {{
                background-color: {cls.PRIMARY};
                color: {cls.PRIMARY_TEXT};
                border: 1px solid {primary_shadow};
                border-bottom: 4px solid {primary_shadow};
                border-radius: 10px;
                padding: 6px 24px 10px 24px;
                font-size: {fs_md}px;
                font-weight: 600;
                font-family: 'Segoe UI', sans-serif;
            }}
            QPushButton:hover {{
                background-color: {cls.PRIMARY_HOVER};
                border-bottom-color: {primary_hover_shadow};
                margin-top: 1px;
                border-bottom-width: 3px;
                padding-bottom: 9px;
            }}
            QPushButton:pressed {{
                background-color: {cls.PRIMARY};
                border-bottom-width: 0px;
                margin-top: 4px;
                padding-top: 10px;
                padding-bottom: 6px;
            }}
            QPushButton:disabled {{
                background-color: {cls.BG_BORDER};
                border-color: {cls.TEXT_DISABLED};
                color: {cls.TEXT_DISABLED};
                border-bottom: 4px solid {cls.TEXT_DISABLED};
            }}

            /* Inputs */
            QLineEdit, QTextEdit, QComboBox {{
                background-color: {cls.BG_SURFACE};
                border: 1px solid {cls.BG_BORDER};
                border-radius: {radius_md}px;
                padding: 10px 12px;
                font-size: {fs_md}px;
                color: {cls.TEXT_PRIMARY};
                selection-background-color: {cls.PRIMARY};
                selection-color: {cls.PRIMARY_TEXT};
            }}
            QLineEdit:focus, QTextEdit:focus, QComboBox:focus {{
                border: 2px solid {cls.PRIMARY};
                background-color: {cls.BG_MAIN};
            }}
            QLineEdit::placeholder, QTextEdit::placeholder {{
                color: {cls.TEXT_SECONDARY};
            }}

            /* Tabs - Right Sidebar */
            QTabWidget#right_sidebar {{
                background-color: {cls.SIDEBAR_BG};
            }}
            QTabWidget#right_sidebar::pane {{
                border: none;
                background: {cls.SIDEBAR_BG};
                border-left: 1px solid {cls.BG_BORDER};
            }}
            QTabWidget::pane {{
                border: none;
                background: {cls.BG_MAIN};
            }}
            QTabBar::tab {{
                background: transparent;
                color: {cls.TEXT_SECONDARY};
                padding: 10px 16px;
                margin: 0 4px;
                border-bottom: 2px solid transparent;
                font-weight: 500;
            }}
            QTabBar::tab:selected {{
                color: {cls.PRIMARY};
                border-bottom: 2px solid {cls.PRIMARY};
            }}
            QTabBar::tab:hover:!selected {{
                background-color: {cls.BG_HOVER};
                border-radius: {radius_sm}px;
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

            QLabel[msg_type="timestamp"] {{
                color: {cls.TEXT_SECONDARY};
                font-size: {fs_sm}px;
                background: transparent;
            }}
            
            /* Checkbox & Radio */
            QRadioButton, QCheckBox {{
                spacing: 8px;
                color: {cls.TEXT_PRIMARY};
            }}
            QRadioButton::indicator, QCheckBox::indicator {{
                width: 18px;
                height: 18px;
                border: 2px solid {cls.SECONDARY};
                background: {cls.BG_MAIN};
                border-radius: 4px;
            }}
            QRadioButton::indicator {{
                border-radius: 10px;
            }}
            QRadioButton::indicator:checked {{
                background-color: {cls.PRIMARY};
                border: 4px solid {cls.BG_MAIN}; 
                outline: 1px solid {cls.PRIMARY}; 
            }}
            QCheckBox::indicator:checked {{
                background-color: {cls.PRIMARY};
                border: 2px solid {cls.PRIMARY};
            }}

            /* Scrollbars */
            QScrollBar:vertical {{
                border: none;
                background: transparent;
                width: 8px;
                margin: 0;
            }}
            QScrollBar::handle:vertical {{
                background: {cls.BG_BORDER};
                min-height: 24px;
                border-radius: 4px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {cls.TEXT_DISABLED};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
                background: none;
            }}
            
            /* === Suggestion & Memory Panels === */
            QWidget#suggestion_panel {{
                background-color: {cls.SUGGESTION_BG};
            }}
            QWidget#memory_viewer {{
                background-color: {cls.BG_MAIN};
            }}
            
            QLabel[role="panel_title"] {{
                font-weight: bold;
                font-size: {fs_md + 2}px;
                color: {cls.TEXT_PRIMARY};
            }}
            /* Specific override for suggestion panel title */
            QWidget#suggestion_panel QLabel[role="panel_title"] {{
                color: {cls.SUGGESTION_TEXT};
            }}

            QScrollArea[role="panel_scroll"] {{
                border: 1px solid {cls.BG_BORDER};
                border-radius: {radius_md}px;
                background-color: {cls.SUGGESTION_BG};
            }}
            /* Force solid background on scroll area viewports to prevent ghosting */
            QScrollArea[role="panel_scroll"] > QWidget > QWidget {{
                background-color: {cls.BG_MAIN};
            }}
            
            /* Target the widget inside ScrollArea - MUST have solid background for repaint */
            QWidget#suggestion_container {{
                background-color: {cls.SUGGESTION_BG};
            }}
            QWidget#memory_container {{
                background-color: {cls.BG_MAIN};
            }}

            QWidget[role="card"], QFrame[role="card"] {{
                background-color: {cls.SUGGESTION_BG};
                color: {cls.SUGGESTION_TEXT};
                border: 1px solid {cls.BG_BORDER};
                border-radius: {radius_sm}px;
            }}
            QLabel[role="card_title"] {{
                font-weight: bold;
                font-size: {fs_md}px;
                color: {cls.SUGGESTION_TEXT};
            }}
            QTextEdit[role="card_content"] {{
                border: 1px solid {cls.BG_BORDER};
                border-radius: {radius_sm}px;
                background-color: {cls.SUGGESTION_BG};
                color: {cls.SUGGESTION_TEXT};
                font-size: {fs_md}px;
            }}
            QPushButton[role="action_button"] {{
                background-color: {cls.PRIMARY};
                color: {cls.PRIMARY_TEXT};
                border: 1px solid {primary_shadow};
                border-bottom: 3px solid {primary_shadow};
                border-radius: {radius_sm}px;
                padding: 4px 12px 6px 12px;
                font-weight: bold;
            }}
            QPushButton[role="action_button"]:hover {{
                background-color: {cls.PRIMARY_HOVER};
                border-bottom-color: {primary_hover_shadow};
                margin-top: 1px;
                border-bottom-width: 2px;
                padding-bottom: 5px;
            }}
            QPushButton[role="action_button"]:pressed {{
                border-bottom-width: 0px;
                margin-top: 3px;
                padding-top: 7px;
                padding-bottom: 3px;
            }}
            
            QPushButton[role="danger_button"] {{
                background-color: {cls.ERROR};
                color: {cls.PRIMARY_TEXT};
                border: 1px solid {error_shadow};
                border-bottom: 3px solid {error_shadow};
                border-radius: {radius_sm}px;
                padding: 3px 12px 5px 12px;
                font-size: {fs_md - 2}px;
            }}
            QPushButton[role="danger_button"]:pressed {{
                border-bottom-width: 0px;
                margin-top: 3px;
                padding-top: 6px;
                padding-bottom: 2px;
            }}
            QLabel[role="loading_text"], QLabel[role="empty_text"], QLabel[role="timestamp"] {{
                color: {cls.TEXT_SECONDARY};
            }}
            
            /* Category Badges */
            QLabel[role="category_badge"] {{
                font-weight: bold; 
                font-size: {fs_md - 2}px;
                padding: 2px 8px;
                border-radius: 3px;
                color: {cls.TEXT_DISABLED}; /* Default */
                background-color: rgba(150, 150, 150, 0.2);
            }}
            QLabel[category="event"] {{ color: {cls.PRIMARY}; background-color: {cls.PRIMARY}33; }}
            QLabel[category="agreement"] {{ color: {cls.SUCCESS}; background-color: {cls.SUCCESS}33; }}
            QLabel[category="topic"] {{ color: {cls.ACCENT}; background-color: {cls.ACCENT}33; }}
            
            /* === Avatar === */
            /* Ensure avatar text is always visible on pastel backgrounds */
            QLabel[role="avatar"] {{
                color: #000000;
                font-weight: bold;
                border: 2px solid {cls.BG_MAIN};
            }}

            /* --- Specific Widget Styling --- */
            
            /* Sidebar - now using sidebar color for visual hierarchy */
            QWidget#sidebar {{
                background-color: {cls.SIDEBAR_BG};
                border-right: 1px solid {cls.BG_BORDER};
            }}
            
            /* Chat Area - Pure white with subtle styling */
            QWidget#chat_container {{
                background-color: {cls.CHAT_BG};
            }}
            
            /* Message Display Area - White background */
            QListWidget#message_display {{
                background-color: {cls.CHAT_BG};
                border: none;
            }}
            
            /* ========== MODERN FLOATING INPUT CAPSULE ========== */
            QWidget#input_container {{
                background-color: {cls.CHAT_BG};
                border: none;
                padding: 8px;
            }}
            
            /* Floating Capsule Input Field */
            QLineEdit#message_input {{
                background-color: {cls.SIDEBAR_BG};
                border: 2px solid {cls.BG_BORDER};
                border-radius: 24px;
                padding: 12px 20px;
                font-size: {fs_md}px;
                color: {cls.TEXT_PRIMARY};
                margin: 8px 16px;
            }}
            QLineEdit#message_input:focus {{
                border: 2px solid {cls.PRIMARY};
                background-color: {cls.CHAT_BG};
            }}
            QLineEdit#message_input::placeholder {{
                color: {cls.TEXT_SECONDARY};
            }}
            
            /* Circular Send Button */
            QPushButton#send_button {{
                background-color: {cls.PRIMARY};
                color: {cls.PRIMARY_TEXT};
                border: none;
                border-radius: 22px;
                min-width: 44px;
                max-width: 44px;
                min-height: 44px;
                max-height: 44px;
                font-size: 16px;
                font-weight: bold;
                margin-right: 16px;
            }}
            QPushButton#send_button:hover {{
                background-color: {cls.PRIMARY_HOVER};
            }}
            QPushButton#send_button:pressed {{
                background-color: {cls.BUBBLE_GRADIENT_START};
            }}
            
            /* Sidebar Lists */
            QListWidget#room_list, QListWidget#user_list {{
                background-color: {cls.SIDEBAR_BG};
            }}
            QListWidget#room_list::item, QListWidget#user_list::item {{
                padding: 10px 16px;
                border-radius: {radius_md}px;
                color: {cls.TEXT_PRIMARY};
            }}
            QListWidget#room_list::item:selected, QListWidget#user_list::item:selected {{
                background-color: {cls.BG_SELECTED};
                color: {cls.TEXT_PRIMARY};
                font-weight: 600;
            }}
            QListWidget#room_list::item:hover:!selected, QListWidget#user_list::item:hover:!selected {{
                background-color: {cls.BG_HOVER};
            }}
            
            /* ========== MODERN GRADIENT CHAT BUBBLES ========== */
            /* User Message - Purple gradient */
            QLabel[msg_type="me"] {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 {cls.BUBBLE_GRADIENT_START}, 
                    stop:1 {cls.BUBBLE_GRADIENT_END});
                color: #FFFFFF;
                border-radius: 16px;
                padding: 12px 16px;
                font-size: {fs_md}px;
            }}
            
            /* AI/Other Message - Light grey */
            QLabel[msg_type="other"] {{
                background-color: {cls.BUBBLE_OTHER_BG};
                color: {cls.TEXT_PRIMARY};
                border-radius: 16px;
                padding: 12px 16px;
                border: none;
                font-size: {fs_md}px;
            }}
            
            QLabel[msg_type="time"] {{
                color: {cls.TEXT_SECONDARY};
                font-size: {fs_sm}px;
                padding: 4px 12px;
                border-radius: {radius_sm}px;
                background-color: {cls.BG_MUTED};
            }}
            
            QLabel[msg_type="sender_name"] {{
                color: {cls.TEXT_SECONDARY};
                font-size: {fs_sm}px;
                font-weight: bold;
                background: transparent;
            }}
            
            QLabel[msg_type="empty_state"] {{
                color: {cls.TEXT_DISABLED};
                font-size: 16px;
                font-weight: bold;
                background: transparent;
            }}

            /* Headers */
            QLabel[header="true"] {{
                color: {cls.TEXT_SECONDARY};
                font-size: {fs_sm}px;
                font-weight: 600;
            }}
            
            /* Status Bar */
            QStatusBar {{
                background-color: {cls.BG_MUTED};
                border-top: 1px solid {cls.BG_BORDER};
                color: {cls.TEXT_SECONDARY};
            }}
        """


class DarkTheme(Theme):
    """Dark Mode Color Palette"""
    
    # Material Design 3 Dark Code Palette
    PRIMARY = "#D0BCFF"       # M3 Light Purple
    PRIMARY_HOVER = "#E8DEF8" 
    PRIMARY_TEXT = "#381E72"  # Dark text on primary
    
    SECONDARY = "#CCC2DC"
    ACCENT = "#EFB8C8"
    
    # Backgrounds - Dark Mode
    BG_MAIN = "#141218"       # Very dark (almost black)
    BG_ELEVATED = "#1D1B20"   # Surface 1
    BG_SURFACE = "#2B2930"    # Surface 2
    BG_MUTED = "#211F26"
    BG_BORDER = "#49454F"     # Dark outline
    BG_HOVER = "#332F37"
    BG_SELECTED = "#4A4458"
    
    # Modern Layout - Visual Hierarchy (Dark Mode)
    SIDEBAR_BG = "#1A1A2E"    # Deep blue-grey for sidebars
    CHAT_BG = "#16161E"       # Slightly lighter dark for chat
    CHAT_PATTERN = "#2A2A3E"  # Dot grid pattern color (dark)
    
    # Gradient colors for user chat bubble (Dark Mode)
    BUBBLE_GRADIENT_START = "#9333EA"  # Vibrant purple
    BUBBLE_GRADIENT_END = "#C084FC"    # Lighter purple
    BUBBLE_OTHER_BG = "#2B2930"        # Dark grey for AI/other messages
    
    # Text Colors
    TEXT_PRIMARY = "#E6E1E5"
    TEXT_SECONDARY = "#CAC4D0"
    TEXT_DISABLED = "#979797"

    # Suggestion Module Colors
    SUGGESTION_BG = "#1E293B"
    SUGGESTION_TEXT = "#F5F7FA"
    SUGGESTION_SHADOW_COLOR = (0, 0, 0, 51) # 0.2 alpha
    
    SUCCESS = "#8CD69D"
    WARNING = "#DCC486"
    ERROR = "#F2B8B5"
