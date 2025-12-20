"""Memory viewer widget for displaying and managing extracted memories"""
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QScrollArea, QTextEdit, QMessageBox,
                             QFrame)
from PyQt6.QtCore import Qt, pyqtSignal
from typing import List, Dict


class MemoryViewer(QWidget):
    """Widget for viewing and managing memories"""
    
    clear_requested = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.memories: List[Dict] = []
        self._init_ui()
    
    def _init_ui(self):
        """Initialize UI components"""
        layout = QVBoxLayout()
        layout.setSpacing(10)
        
        # Header
        header_layout = QHBoxLayout()
        title_label = QLabel("🧠 对话记忆")
        title_label.setStyleSheet("font-weight: bold; font-size: 15px; color: #111827;")
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        
        clear_btn = QPushButton("清空记忆")
        clear_btn.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 5px 15px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
        """)
        clear_btn.clicked.connect(self._on_clear_requested)
        header_layout.addWidget(clear_btn)
        
        layout.addLayout(header_layout)
        
        # Scroll area for memories
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: 1px solid #ddd;
                border-radius: 5px;
                background-color: white;
            }
        """)
        
        self.memory_container = QWidget()
        self.memory_layout = QVBoxLayout()
        self.memory_container.setLayout(self.memory_layout)
        scroll_area.setWidget(self.memory_container)
        
        layout.addWidget(scroll_area)
        
        # Empty state
        self.empty_label = QLabel("暂无记忆\n对话中的关键信息将自动提取并显示在这里")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.setStyleSheet("color: #999; padding: 20px;")
        self.memory_layout.addWidget(self.empty_label)
        self.memory_layout.addStretch()
        
        self.setLayout(layout)
        self.setStyleSheet("""
            QWidget {
                background-color: #fafafa;
                padding: 10px;
            }
        """)
    
    def update_memories(self, memories: List[Dict]):
        """Update displayed memories"""
        self.memories = memories
        self._refresh_display()
    
    def _refresh_display(self):
        """Refresh memory display"""
        # Clear existing memory cards
        while self.memory_layout.count():
            item = self.memory_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        if not self.memories:
            # Show empty state
            self.empty_label = QLabel("暂无记忆\n对话中的关键信息将自动提取并显示在这里")
            self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.empty_label.setStyleSheet("color: #999; padding: 20px;")
            self.memory_layout.addWidget(self.empty_label)
        else:
            # Hide empty label if exists
            if hasattr(self, 'empty_label') and self.empty_label:
                self.empty_label.hide()
            
            # Add memory cards
            for memory in self.memories:
                card = self._create_memory_card(memory)
                self.memory_layout.addWidget(card)
        
        self.memory_layout.addStretch()
    
    def _create_memory_card(self, memory: Dict) -> QWidget:
        """Create a memory card widget"""
        card = QFrame()
        card.setFrameShape(QFrame.Shape.StyledPanel)
        card.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                padding: 10px;
                margin: 5px 0px;
            }
        """)
        
        layout = QVBoxLayout()
        layout.setSpacing(5)
        
        # Category badge
        category = memory.get('category', 'unknown')
        category_colors = {
            'event': '#3498db',
            'agreement': '#2ecc71',
            'topic': '#9b59b6',
            'unknown': '#95a5a6'
        }
        color = category_colors.get(category, '#95a5a6')
        
        category_label = QLabel(f"📌 {category}")
        category_label.setStyleSheet(f"""
            color: {color};
            font-weight: bold;
            font-size: 11px;
            padding: 2px 8px;
            background-color: {color}20;
            border-radius: 3px;
        """)
        layout.addWidget(category_label)
        
        # Content
        content_text = QTextEdit()
        content_text.setPlainText(memory.get('content', ''))
        content_text.setReadOnly(True)
        content_text.setMaximumHeight(80)
        content_text.setStyleSheet("""
            QTextEdit {
                border: none;
                background-color: transparent;
                font-size: 14px;
                color: #111827;
            }
        """)
        layout.addWidget(content_text)
        
        # Timestamp
        if 'created_at' in memory:
            timestamp_label = QLabel(f"记录时间: {memory['created_at'][:19]}")
            timestamp_label.setStyleSheet("color: #999; font-size: 10px;")
            layout.addWidget(timestamp_label)
        
        card.setLayout(layout)
        return card
    
    def _on_clear_requested(self):
        """Handle clear button click"""
        if not self.memories:
            return
        
        reply = QMessageBox.question(
            self,
            "确认清空",
            "确定要清空所有记忆吗？此操作不可恢复。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.clear_requested.emit()

