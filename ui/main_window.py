"""Main window for pet-chat application"""
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QLineEdit, QPushButton, QSplitter,
                             QLabel, QScrollArea, QMessageBox, QMenuBar, QMenu,
                             QTabWidget, QListWidget, QListWidgetItem, QFrame)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QTextCharFormat, QColor, QTextCursor, QAction
from datetime import datetime
from typing import Optional
import json

from ui.pet_widget import PetWidget
from ui.suggestion_panel import SuggestionPanel
from ui.memory_viewer import MemoryViewer
from ui.api_config_dialog import APIConfigDialog


class MainWindow(QMainWindow):
    """Main application window"""
    
    message_sent = pyqtSignal(str, str)
    ai_requested = pyqtSignal()
    api_config_changed = pyqtSignal(str, str, bool)
    api_config_reset = pyqtSignal()
    
    def __init__(self, is_host: bool = False, parent=None):
        super().__init__(parent)
        self.is_host = is_host
        self.user_name = "Host" if is_host else "Guest"
        self.message_history = []
        self._init_ui()
    
    def _init_ui(self):
        """Initialize UI components"""
        self.setWindowTitle(f"pet-chat - {self.user_name}")
        self.setGeometry(100, 100, 1400, 900)
        
        # Menu bar
        self._create_menu_bar()
        
        # Central widget
        central_widget = QWidget()
        central_widget.setObjectName("central")
        self.setCentralWidget(central_widget)
        
        self.setStyleSheet("""
            QWidget#central {
                background-color: #e5e7eb;
            }
            QMenuBar {
                background-color: #ffffff;
                border-bottom: 1px solid #e5e7eb;
            }
            QMenuBar::item {
                padding: 4px 12px;
            }
            QMenuBar::item:selected {
                background-color: #e5e7eb;
            }
            QStatusBar {
                background-color: #ffffff;
                border-top: 1px solid #e5e7eb;
            }
            QTabWidget::pane {
                border: 1px solid #e5e7eb;
                border-radius: 10px;
                background-color: #ffffff;
            }
            QTabBar::tab {
                background-color: #e5e7eb;
                padding: 6px 12px;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background-color: #ffffff;
            }
        """)
        
        # Main layout with splitter
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(5, 5, 5, 5)
        
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left side: Chat area + Pet
        left_widget = QWidget()
        left_layout = QVBoxLayout()
        left_layout.setSpacing(10)
        
        # Pet widget
        self.pet_widget = PetWidget()
        self.pet_widget.setMaximumHeight(180)
        left_layout.addWidget(self.pet_widget)
        
        # Chat area
        chat_container = QWidget()
        chat_layout = QVBoxLayout()
        chat_layout.setSpacing(8)
        
        # Message display (WeChat-style bubble list)
        self.message_display = QListWidget()
        self.message_display.setFrameShape(QFrame.Shape.NoFrame)
        self.message_display.setStyleSheet("""
            QListWidget {
                background-color: #f9fafb;
                border: none;
            }
        """)
        chat_layout.addWidget(self.message_display)
        
        # Input area
        input_layout = QHBoxLayout()
        input_layout.setSpacing(8)
        self.message_input = QLineEdit()
        self.message_input.setPlaceholderText("输入消息... (输入 /ai 请求AI建议)")
        self.message_input.returnPressed.connect(self._send_message)
        self.message_input.setStyleSheet("""
            QLineEdit {
                padding: 10px;
                border: 2px solid #ddd;
                border-radius: 8px;
                font-size: 14px;
                background-color: #f9fafb;
                color: #111827;
            }
            QLineEdit:focus {
                border: 2px solid #3498db;
            }
        """)
        input_layout.addWidget(self.message_input)
        
        self.send_button = QPushButton("发送")
        self.send_button.clicked.connect(self._send_message)
        self.send_button.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 10px 25px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QPushButton:pressed {
                background-color: #21618c;
            }
        """)
        input_layout.addWidget(self.send_button)
        
        chat_layout.addLayout(input_layout)
        chat_container.setLayout(chat_layout)
        
        left_layout.addWidget(chat_container)
        left_widget.setLayout(left_layout)
        
        # Right side: Tab widget for suggestions and memories
        right_tabs = QTabWidget()
        right_tabs.setMaximumWidth(350)
        
        # Suggestion panel
        self.suggestion_panel = SuggestionPanel()
        self.suggestion_panel.suggestion_adopted.connect(self._on_suggestion_adopted)
        right_tabs.addTab(self.suggestion_panel, "💡 建议")
        
        # Memory viewer
        self.memory_viewer = MemoryViewer()
        self.memory_viewer.clear_requested.connect(self._on_clear_memories)
        right_tabs.addTab(self.memory_viewer, "🧠 记忆")
        
        splitter.addWidget(left_widget)
        splitter.addWidget(right_tabs)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)
        
        main_layout.addWidget(splitter)
        central_widget.setLayout(main_layout)
        
        # Status bar
        self.statusBar().showMessage(f"已连接 - {self.user_name}")
        self.statusBar().setStyleSheet("""
            QStatusBar {
                background-color: #f8f9fa;
                border-top: 1px solid #dee2e6;
                color: #555555;
            }
        """)
    
    def _create_menu_bar(self):
        """Create menu bar"""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("文件")
        exit_action = QAction("退出", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        settings_menu = menubar.addMenu("设置")
        if self.is_host:
            api_action = QAction("⚙ API 配置", self)
            api_action.setShortcut("Ctrl+K")
            api_action.triggered.connect(self._show_api_config)
            settings_menu.addAction(api_action)
        
        # View menu
        view_menu = menubar.addMenu("视图")
        
        memories_action = QAction("查看记忆", self)
        memories_action.setShortcut("Ctrl+M")
        memories_action.triggered.connect(self._show_memories_tab)
        view_menu.addAction(memories_action)
        
        # Help menu
        help_menu = menubar.addMenu("帮助")
        
        about_action = QAction("关于", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)
    
    def add_message(self, sender: str, content: str, timestamp: Optional[str] = None):
        """
        Add a message to the chat display
        
        Args:
            sender: Message sender name
            content: Message content
            timestamp: Optional timestamp (defaults to now)
        """
        if timestamp is None:
            timestamp = datetime.now().strftime("%H:%M:%S")
        
        self.message_history.append({"sender": sender, "content": content, "timestamp": timestamp})
        
        bubble_widget = QWidget()
        bubble_layout = QHBoxLayout()
        bubble_layout.setContentsMargins(10, 5, 10, 5)
        bubble_layout.setSpacing(10)

        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(4)

        text_label = QLabel(content)
        text_label.setWordWrap(True)
        text_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

        time_label = QLabel(timestamp)
        time_label.setStyleSheet("color: #9ca3af; font-size: 10px;")

        if sender == self.user_name:
            text_label.setStyleSheet("""
                QLabel {
                    background-color: #95ec69;
                    color: #111827;
                    border-radius: 10px;
                    padding: 8px 12px;
                    font-size: 14px;
                }
            """)
        else:
            text_label.setStyleSheet("""
                QLabel {
                    background-color: #ffffff;
                    color: #111827;
                    border-radius: 10px;
                    padding: 8px 12px;
                    font-size: 14px;
                }
            """)

        content_layout.addWidget(text_label)
        content_layout.addWidget(time_label, 0, Qt.AlignmentFlag.AlignRight)

        if sender == self.user_name:
            bubble_layout.addStretch()
            bubble_layout.addLayout(content_layout)
        else:
            bubble_layout.addLayout(content_layout)
            bubble_layout.addStretch()

        bubble_widget.setLayout(bubble_layout)

        item = QListWidgetItem()
        item.setSizeHint(bubble_widget.sizeHint())
        self.message_display.addItem(item)
        self.message_display.setItemWidget(item, bubble_widget)
        self.message_display.scrollToBottom()
    
    def _send_message(self):
        """Handle send message"""
        content = self.message_input.text().strip()
        if not content:
            return
        
        # Check for /ai command
        if content == "/ai":
            self.ai_requested.emit()
            self.message_input.clear()
            return
        
        # Emit signal to send message
        self.message_sent.emit(self.user_name, content)
        
        # Add to display
        self.add_message(self.user_name, content)
        
        # Clear input
        self.message_input.clear()
    
    def _on_suggestion_adopted(self, content: str):
        """Handle suggestion adoption"""
        # Insert suggestion content into input field
        self.message_input.setText(content)
        self.message_input.setFocus()
    
    def update_emotion(self, emotion_scores: dict):
        """Update pet emotion display"""
        self.pet_widget.update_emotion(emotion_scores)
    
    def show_suggestion(self, suggestion: dict):
        """Display an AI suggestion"""
        self.suggestion_panel.show_suggestion(suggestion)
    
    def update_status(self, message: str):
        """Update status bar"""
        self.statusBar().showMessage(message)
    
    def update_memories(self, memories: list):
        """Update memory viewer"""
        self.memory_viewer.update_memories(memories)
    
    def _show_api_config(self):
        """Show API configuration dialog"""
        dialog = APIConfigDialog(parent=self)
        dialog.config_applied.connect(self._on_api_config_applied)
        dialog.config_reset.connect(self._on_api_config_reset)
        dialog.exec()
    
    def _on_api_config_applied(self, api_key: str, api_base: str, persist: bool):
        """Handle API config apply"""
        self.api_config_changed.emit(api_key, api_base, persist)
    
    def _on_api_config_reset(self):
        """Handle API config reset"""
        self.api_config_reset.emit()
    
    def _show_memories_tab(self):
        """Switch to memories tab"""
        # Find the tab widget and switch to memories tab
        for widget in self.findChildren(QTabWidget):
            widget.setCurrentIndex(1)
    
    def _on_clear_memories(self):
        """Handle clear memories request"""
        # Signal will be handled by app controller
        pass
    
    def _show_about(self):
        """Show about dialog"""
        QMessageBox.about(
            self,
            "关于 pet-chat",
            "pet-chat v1.0\n\n"
            "一个探索 AI 作为\"第三方观察者\"介入聊天场景的实验性项目。\n\n"
            "功能特性：\n"
            "• P2P 点对点聊天\n"
            "• 情绪宠物系统\n"
            "• 对话记忆提取\n"
            "• AI 决策辅助\n\n"
            "实验项目，仅供学习交流使用。"
        )

