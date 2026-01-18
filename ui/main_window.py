"""Main window for pet-chat application"""
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QLineEdit, QPushButton, QSplitter,
                             QLabel, QScrollArea, QMessageBox, QMenuBar, QMenu,
                             QTabWidget, QListWidget, QListWidgetItem, QFrame,
                             QInputDialog)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QTextCharFormat, QColor, QTextCursor, QAction
from datetime import datetime
from typing import Optional
import json

from ui.pet_widget import PetWidget
from ui.suggestion_panel import SuggestionPanel
from ui.memory_viewer import MemoryViewer
from ui.api_config_dialog import APIConfigDialog
from ui.theme import Theme


class MainWindow(QMainWindow):
    """Main application window"""
    
    message_sent = pyqtSignal(str, str)
    ai_requested = pyqtSignal()
    api_config_changed = pyqtSignal(str, str, bool)
    api_config_reset = pyqtSignal()
    conversation_selected = pyqtSignal(str)
    load_more_requested = pyqtSignal()
    typing_changed = pyqtSignal(bool)
    reset_user_requested = pyqtSignal()  # Request to reset local user data
    user_selected = pyqtSignal(str, str)  # user_id, user_name for starting chat
    
    
    def __init__(self, user_id: str, user_name: Optional[str] = None, user_avatar: Optional[str] = None, parent=None):
        super().__init__(parent)
        self.user_id = user_id
        self.user_name = user_name if user_name else "User"
        self.user_avatar = user_avatar if user_avatar else ""
        self.message_history = []
        self._current_is_group = False
        self._typing = False
        self._init_ui()
        self._init_sidebar_data()
    
    def _init_ui(self):
        """Initialize UI components"""
        self.setWindowTitle(f"pet-chat - {self.user_name}")
        self.setGeometry(100, 100, 1400, 900)
        
        self._create_menu_bar()
        
        # Central widget
        central_widget = QWidget()
        central_widget.setObjectName("central")
        self.setCentralWidget(central_widget)

        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(5, 5, 5, 5)
        
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        sidebar_widget = QWidget()
        sidebar_widget.setObjectName("sidebar")
        sidebar_widget.setStyleSheet(f"#sidebar {{ background-color: {Theme.BG_ELEVATED}; border-right: 1px solid {Theme.BG_BORDER}; }}")
        sidebar_layout = QVBoxLayout()
        sidebar_layout.setSpacing(8)
        sidebar_layout.setContentsMargins(0, 0, 8, 0)
        
        room_header_layout = QHBoxLayout()
        room_label = QLabel("会话列表")
        room_label.setStyleSheet(
            f"color: {Theme.TEXT_SECONDARY}; font-size: {Theme.FONT_SIZE_SM}px; font-weight: 600;"
        )
        room_header_layout.addWidget(room_label)
        room_header_layout.addStretch()
        self.new_group_button = QPushButton("新建群聊")
        self.new_group_button.setFixedHeight(24)
        self.new_group_button.clicked.connect(self._on_new_group_clicked)
        self.new_group_button.hide()
        room_header_layout.addWidget(self.new_group_button)
        sidebar_layout.addLayout(room_header_layout)
        
        self.room_list = QListWidget()
        self.room_list.setStyleSheet(
            f"QListWidget {{ background-color: transparent; border: none; outline: none; }}"
            f"QListWidget::item {{ padding: 10px 16px; border-radius: {Theme.RADIUS_MD}px; }}"
            f"QListWidget::item:selected {{ background-color: {Theme.BG_SELECTED}; color: {Theme.PRIMARY}; font-weight: 600; }}"
            f"QListWidget::item:hover:!selected {{ background-color: {Theme.BG_HOVER}; }}"
        )
        self.room_list.itemSelectionChanged.connect(self._on_room_selected)
        sidebar_layout.addWidget(self.room_list)
        
        user_label = QLabel("在线用户")
        user_label.setStyleSheet(
            f"color: {Theme.TEXT_SECONDARY}; font-size: {Theme.FONT_SIZE_SM}px; font-weight: 600;"
        )
        sidebar_layout.addWidget(user_label)
        
        self.user_list = QListWidget()
        self.user_list.setStyleSheet(
            f"QListWidget {{ background-color: transparent; border: none; outline: none; }}"
            f"QListWidget::item {{ padding: 8px 16px; border-radius: {Theme.RADIUS_MD}px; }}"
            f"QListWidget::item:selected {{ background-color: {Theme.BG_SELECTED}; color: {Theme.TEXT_PRIMARY}; }}"
        )
        self.user_list.itemSelectionChanged.connect(self._on_user_selected)
        sidebar_layout.addWidget(self.user_list)
        
        sidebar_layout.addStretch()
        sidebar_widget.setLayout(sidebar_layout)
        sidebar_widget.setMinimumWidth(220)
        
        left_widget = QWidget()
        left_layout = QVBoxLayout()
        left_layout.setSpacing(10)
        
        # PetWidget is now a floating overlay, not added to layout
        
        chat_container = QWidget()
        chat_layout = QVBoxLayout()
        chat_layout.setSpacing(8)

        self.load_more_button = QPushButton("加载更多消息")
        self.load_more_button.clicked.connect(self._on_load_more_clicked)
        chat_layout.addWidget(self.load_more_button)
        
        self.message_display = QListWidget()
        self.message_display.setFrameShape(QFrame.Shape.NoFrame)
        self.message_display.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.message_display.setVerticalScrollMode(QListWidget.ScrollMode.ScrollPerPixel)
        self.message_display.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        self.message_display.setStyleSheet(
            f"QListWidget {{ background-color: {Theme.BG_MAIN}; border: none; }}"
        )
        chat_layout.addWidget(self.message_display)
        
        input_container = QWidget()
        input_layout = QHBoxLayout()
        input_layout.setContentsMargins(0, 0, 0, 0)
        input_layout.setSpacing(8)
        self.message_input = QLineEdit()
        self.message_input.setPlaceholderText("输入消息... (输入 /ai 请求AI建议)")
        self.message_input.returnPressed.connect(self._send_message)
        self.message_input.textEdited.connect(self._on_text_edited)
        input_layout.addWidget(self.message_input)
        
        self.send_button = QPushButton("发送")
        self.send_button.clicked.connect(self._send_message)
        input_layout.addWidget(self.send_button)
        input_container.setLayout(input_layout)
        
        chat_layout.addWidget(input_container)
        chat_container.setLayout(chat_layout)
        
        left_layout.addWidget(chat_container)
        left_widget.setLayout(left_layout)
        
        right_tabs = QTabWidget()
        right_tabs.setMaximumWidth(350)
        
        self.suggestion_panel = SuggestionPanel()
        self.suggestion_panel.suggestion_adopted.connect(self._on_suggestion_adopted)
        right_tabs.addTab(self.suggestion_panel, "💡 建议")
        
        self.memory_viewer = MemoryViewer()
        self.memory_viewer.clear_requested.connect(self._on_clear_memories)
        right_tabs.addTab(self.memory_viewer, "🧠 记忆")
        
        splitter.addWidget(sidebar_widget)
        splitter.addWidget(left_widget)
        splitter.addWidget(right_tabs)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)
        splitter.setStretchFactor(2, 1)
        
        main_layout.addWidget(splitter)
        central_widget.setLayout(main_layout)
        
        # Initialize floating pet widget (overlay)
        self._init_floating_pet()
        
        self.statusBar().showMessage(f"已连接 - {self.user_name}")
        self.statusBar().setStyleSheet(
            f"QStatusBar {{ background-color: {Theme.BG_MUTED}; border-top: 1px solid {Theme.BG_BORDER}; color: {Theme.TEXT_SECONDARY}; }}"
        )
    
    def _create_menu_bar(self):
        """Create menu bar"""
        menubar = self.menuBar()
        
        file_menu = menubar.addMenu("文件")
        exit_action = QAction("退出", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        self.settings_menu = menubar.addMenu("设置")
        self.api_action = QAction("AI 配置", self)
        self.api_action.setShortcut("Ctrl+K")
        self.api_action.triggered.connect(self._show_api_config)
        self.settings_menu.addAction(self.api_action)
        self.api_action.setEnabled(True) # AI service can be configured by any client
        
        # Add Reset User action
        reset_user_action = QAction("🔄 重置用户数据", self)
        reset_user_action.triggered.connect(self._on_reset_user_requested)
        self.settings_menu.addAction(reset_user_action)
        
        
        view_menu = menubar.addMenu("视图")
        
        memories_action = QAction("查看记忆", self)
        memories_action.setShortcut("Ctrl+M")
        memories_action.triggered.connect(self._show_memories_tab)
        view_menu.addAction(memories_action)
        
        help_menu = menubar.addMenu("帮助")
        
        about_action = QAction("关于", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    def _init_floating_pet(self):
        """Initialize the floating pet widget as an overlay"""
        # Create pet widget with central widget as parent (not added to any layout)
        self.pet_widget = PetWidget(self.centralWidget())
        
        # Enable transparent background
        self.pet_widget.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # Position at bottom-right corner
        self._position_pet_widget()
        
        # Ensure it floats above all other widgets
        self.pet_widget.raise_()
        self.pet_widget.show()
    
    def _position_pet_widget(self):
        """Position pet widget at the bottom-right corner of the central widget"""
        if hasattr(self, 'pet_widget') and self.pet_widget:
            central = self.centralWidget()
            if central:
                x = central.width() - self.pet_widget.width() - 20
                y = central.height() - self.pet_widget.height() - 40
                # Ensure position is not negative
                x = max(20, x)
                y = max(20, y)
                self.pet_widget.move(x, y)
    
    def resizeEvent(self, event):
        """Handle window resize to reposition floating pet"""
        super().resizeEvent(event)
        # Keep pet widget within bounds after resize
        if hasattr(self, 'pet_widget') and self.pet_widget:
            # Only reposition if pet is outside visible area
            pet_x = self.pet_widget.x()
            pet_y = self.pet_widget.y()
            central = self.centralWidget()
            if central:
                max_x = central.width() - self.pet_widget.width()
                max_y = central.height() - self.pet_widget.height()
                if pet_x > max_x or pet_y > max_y:
                    new_x = min(pet_x, max(0, max_x))
                    new_y = min(pet_y, max(0, max_y))
                    self.pet_widget.move(new_x, new_y)

    def _init_sidebar_data(self):
        # Initialize with current user in user list
        current_user_item = QListWidgetItem(self.user_name)
        current_user_item.setData(Qt.ItemDataRole.UserRole, self.user_name)
        self.user_list.addItem(current_user_item)
        self.user_list.setCurrentItem(current_user_item)
        # Conversations will be loaded via load_conversations() after database is ready
    
    def load_conversations(self, conversations: list):
        """Load conversations from database into sidebar"""
        self.room_list.clear()
        
        if not conversations:
            # No conversations yet - create default one
            default_item = QListWidgetItem("Default Chat")
            default_item.setData(Qt.ItemDataRole.UserRole, "default")
            default_item.setData(Qt.ItemDataRole.UserRole + 1, False)  # is_group
            self.room_list.addItem(default_item)
            self.room_list.setCurrentItem(default_item)
            return
        
        # Add each conversation to the list
        for conv in conversations:
            conv_id = conv.get("id", "")
            conv_name = conv.get("name", "Unknown")
            conv_type = conv.get("type", "p2p")
            last_msg = conv.get("last_message", "")
            
            # Create display text with preview
            if last_msg:
                display_text = f"{conv_name}\n{last_msg[:30]}..."
            else:
                display_text = conv_name
            
            item = QListWidgetItem(display_text)
            item.setData(Qt.ItemDataRole.UserRole, conv_id)
            item.setData(Qt.ItemDataRole.UserRole + 1, conv_type == "group")
            self.room_list.addItem(item)
        
        # Select first conversation
        if self.room_list.count() > 0:
            self.room_list.setCurrentRow(0)
    
    def load_online_users(self, users: list):
        """Load online users from database into sidebar"""
        self.user_list.clear()
        
        # Add current user first
        current_user_item = QListWidgetItem(f"{self.user_name} (You)")
        current_user_item.setData(Qt.ItemDataRole.UserRole, None)  # No user_id for self
        self.user_list.addItem(current_user_item)
        
        # Add discovered online users
        for user in users:
            user_id = user.get("id")
            user_name = user.get("name", "Unknown")
            ip = user.get("ip_address", "")
            
            display_text = f"🟢 {user_name}"
            if ip:
                display_text += f" ({ip})"
            
            item = QListWidgetItem(display_text)
            item.setData(Qt.ItemDataRole.UserRole, user_id)
            self.user_list.addItem(item)
        
        print(f"[DEBUG] Loaded {len(users)} online users to UI")
    
    def clear_messages(self):
        self.message_history = []
        self.message_display.clear()
    
    def show_typing_status(self, sender_name: str, is_typing: bool):
        if is_typing:
            self.statusBar().showMessage(f"{sender_name} 正在输入...", 2000)
    
    def add_message(self, sender: str, content: str, timestamp: Optional[str] = None, is_me: bool = None, sender_avatar: str = ""):
        """
        Add a message to the chat display
        Args:
            sender: Name of the message sender
            content: Message content  
            timestamp: Message timestamp
            is_me: True if from current user, False if from others, None to auto-detect
        """
        if timestamp is None:
            timestamp = datetime.now().strftime("%H:%M")
        
        # Auto-detect is_me if not provided (backward compatibility)
        if is_me is None:
            is_me = (sender == self.user_name)

        previous_timestamp = self.message_history[-1]["timestamp"] if self.message_history else None
        self.message_history.append({"sender": sender, "content": content, "timestamp": timestamp})

        show_separator = False
        if previous_timestamp is None:
            show_separator = True
        else:
            show_separator = previous_timestamp[:5] != timestamp[:5]
        if show_separator:
            self._add_time_separator(timestamp)
        
        # Container for the whole row
        bubble_widget = QWidget()
        bubble_widget.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        bubble_layout = QHBoxLayout()
        bubble_layout.setContentsMargins(10, 5, 10, 5)
        bubble_layout.setSpacing(10) # Increased spacing between avatar and bubble

        # Avatar Label Creation (Reusable)
        def create_avatar_label(avatar_str, user_name):
            # 1. Determine background color based on username hash
            colors = [
                "#FFADAD", "#FFD6A5", "#FDFFB6", "#CAFFBF", 
                "#9BF6FF", "#A0C4FF", "#BDB2FF", "#FFC6FF",
                "#E0E0E0", "#FFB5E8", "#B5B9FF", "#85E3FF"
            ]
            hash_val = sum(ord(c) for c in user_name) if user_name else 0
            bg_color = colors[hash_val % len(colors)]
            
            # 2. Determine display content (Emoji mapping or first char)
            # Simple mapping for common avatar keywords
            avatar_map = {
                "cat": "🐱", "dog": "🐶", "monitor": "📊", 
                "robot": "🤖", "user": "👤", "admin": "👨‍⚖️"
            }
            
            content = "👤"
            if avatar_str:
                if avatar_str.lower() in avatar_map:
                    content = avatar_map[avatar_str.lower()]
                else:
                    # If it looks like an emoji (non-ascii), use it
                    # Otherwise use first letter of name or avatar string
                    if len(avatar_str) > 0 and ord(avatar_str[0]) > 127:
                         content = avatar_str
                    elif user_name:
                         content = user_name[0].upper()
                    else:
                         content = avatar_str[:1].upper()
            elif user_name:
                content = user_name[0].upper()

            lbl = QLabel(content)
            lbl.setStyleSheet(
                f"font-size: 20px; background: {bg_color}; border-radius: 20px; "
                f"min-width: 40px; max-width: 40px; min-height: 40px; max-height: 40px;"
                f"border: 2px solid #FFFFFF;" # Add white border for better contrast
            )
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            return lbl

        # Content container (includes username + message)
        content_container = QVBoxLayout()
        content_container.setContentsMargins(0, 0, 0, 0)
        content_container.setSpacing(4)
        
        # Message bubble layout (text + time)
        message_bubble = QVBoxLayout()
        message_bubble.setContentsMargins(0, 0, 0, 0)
        message_bubble.setSpacing(4)

        text_label = QLabel(content)
        text_label.setWordWrap(True)
        text_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        
        # Explicit font setup
        font = text_label.font()
        font.setPointSize(10)
        text_label.setFont(font)

        time_label = QLabel(timestamp)
        time_label.setStyleSheet(
            f"color: {Theme.TEXT_SECONDARY}; font-size: 10px; background: transparent;"
        )

        # Styling based on is_me
        if is_me:
            # Self message
            text_label.setStyleSheet(
                f"background-color: {Theme.PRIMARY}; color: #FFFFFF;"
                f" border-radius: 12px; padding: 10px 14px;"
            )
            message_bubble.addWidget(text_label)
            message_bubble.addWidget(time_label, 0, Qt.AlignmentFlag.AlignRight)
            
            # Add bubble to content container (No username for self)
            content_container.addLayout(message_bubble)
            
            # Layout: [Stretch] [Content] [Avatar]
            bubble_layout.addStretch()
            bubble_layout.addLayout(content_container)
            
            # Avatar for self (Right side)
            avatar_label = create_avatar_label(sender_avatar, sender)
            bubble_layout.addWidget(avatar_label)
            bubble_layout.setAlignment(avatar_label, Qt.AlignmentFlag.AlignTop)
            
        else:
            # Other message
            text_label.setStyleSheet(
                f"background-color: #F2F2F2; color: #000000;"
                f" border-radius: 12px; padding: 10px 14px;"
                f" border: 1px solid {Theme.BG_BORDER};"
            )
            message_bubble.addWidget(text_label)
            message_bubble.addWidget(time_label, 0, Qt.AlignmentFlag.AlignRight)
            
            # Username (only for others)
            username_label = QLabel(sender)
            username_label.setStyleSheet(
                f"color: {Theme.TEXT_SECONDARY}; font-size: 11px; font-weight: bold; background: transparent; margin-bottom: 2px;"
            )
            content_container.addWidget(username_label)
            content_container.addLayout(message_bubble)
            
            # Layout: [Avatar] [Content] [Stretch]
            # Avatar for other (Left side)
            avatar_label = create_avatar_label(sender_avatar, sender)
            bubble_layout.addWidget(avatar_label)
            bubble_layout.setAlignment(avatar_label, Qt.AlignmentFlag.AlignTop)
            
            bubble_layout.addLayout(content_container)
            bubble_layout.addStretch()

        bubble_widget.setLayout(bubble_layout)

        item = QListWidgetItem()
        item.setSizeHint(bubble_widget.sizeHint())
        self.message_display.addItem(item)
        self.message_display.setItemWidget(item, bubble_widget)
        self.message_display.scrollToBottom()

    def _add_time_separator(self, timestamp: str):
        separator_widget = QWidget()
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 8, 0, 8)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        label = QLabel(timestamp)
        label.setStyleSheet(
            f"color: {Theme.TEXT_SECONDARY}; font-size: 11px; padding: 4px 12px;"
            f" border-radius: {Theme.RADIUS_SM}px; background-color: {Theme.BG_MUTED};"
        )
        layout.addWidget(label)
        separator_widget.setLayout(layout)

        item = QListWidgetItem()
        item.setSizeHint(separator_widget.sizeHint())
        self.message_display.addItem(item)
        self.message_display.setItemWidget(item, separator_widget)
    
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
        self.add_message(self.user_name, content, sender_avatar=self.user_avatar)
        
        # Clear input
        self.message_input.clear()
    
    def _on_suggestion_adopted(self, content: str):
        """Handle suggestion adoption"""
        existing = self.message_input.text()
        if existing.strip():
            new_text = existing.rstrip() + "\n" + content
        else:
            new_text = content
        self.message_input.setText(new_text)
        self.message_input.setCursorPosition(len(new_text))
        self.message_input.setFocus()
        self.statusBar().showMessage("已将 AI 建议放入输入框，请确认后发送。", 5000)
    
    def _on_room_selected(self):
        items = self.room_list.selectedItems()
        if not items:
            return
        item = items[0]
        room_name = item.text()
        conversation_id = item.data(Qt.ItemDataRole.UserRole) or "default"
        is_group = bool(item.data(Qt.ItemDataRole.UserRole + 1))
        self._current_is_group = is_group
        self.statusBar().showMessage(f"已切换到会话：{room_name}", 3000)
        self.conversation_selected.emit(conversation_id)
    
    def _on_user_selected(self):
        items = self.user_list.selectedItems()
        if not items:
            return
        item = items[0]
        user_id = item.data(Qt.ItemDataRole.UserRole)
        
        # Skip if selecting yourself
        if not user_id:
            self.statusBar().showMessage("这是你自己", 2000)
            return
        
        # Extract user_name from display text (remove 🟢 and IP address)
        user_name = item.text().replace("🟢 ", "").split(" (")[0]
        
        self.statusBar().showMessage(f"开始与 {user_name} 的对话", 3000)
        
        # Emit signal to create/open conversation
        self.user_selected.emit(user_id, user_name)

    def _on_load_more_clicked(self):
        self.load_more_requested.emit()

    def _on_new_group_clicked(self):
        name, ok = QInputDialog.getText(self, "新建群聊", "请输入群聊名称：")
        if not ok:
            return
        name = name.strip() or "新的群聊"
        conversation_id = f"group-{int(datetime.now().timestamp())}"
        item = QListWidgetItem(name)
        item.setData(Qt.ItemDataRole.UserRole, conversation_id)
        item.setData(Qt.ItemDataRole.UserRole + 1, True)
        self.room_list.addItem(item)
        self.room_list.setCurrentItem(item)

    def _on_text_edited(self, _text: str):
        text = self.message_input.text()
        now_typing = bool(text.strip())
        if now_typing != self._typing:
            self._typing = now_typing
            self.typing_changed.emit(now_typing)
    
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
    
    def _on_reset_user_requested(self):
        """Handle reset user data request"""
        reply = QMessageBox.question(
            self,
            "重置用户数据",
            "此操作将清除本地用户信息，并重新生成新的用户ID。\n"
            "应用程序将重启。\n\n"
            "确定要继续吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.reset_user_requested.emit()
    
    def _show_about(self):
        """Show about dialog"""
        QMessageBox.about(
            self,
            "关于 pet-chat",
            "pet-chat v1.1\n\n"
            "功能特性：\n"
            "• Client-Server 架构聊天\n"
            "• 情绪宠物系统\n"
            "• 对话记忆提取\n"
            "• AI 决策辅助\n\n"
        )

