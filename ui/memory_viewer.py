"""Memory viewer widget for displaying and managing extracted memories"""
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QScrollArea, QTextEdit, QMessageBox,
                             QFrame)
from PyQt6.QtCore import Qt, pyqtSignal
from typing import List, Dict
from ui.theme import Theme


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
        
        header_layout = QHBoxLayout()
        title_label = QLabel("🧠 对话记忆")
        title_label.setProperty("role", "panel_title")
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        
        clear_btn = QPushButton("清空记忆")
        clear_btn.setProperty("role", "danger_button")
        clear_btn.clicked.connect(self._on_clear_requested)
        header_layout.addWidget(clear_btn)
        
        layout.addLayout(header_layout)
        
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setProperty("role", "panel_scroll")
        # Disable static contents to prevent ghosting/trailing artifacts when overlays move over
        scroll_area.viewport().setAttribute(Qt.WidgetAttribute.WA_StaticContents, False)
        
        self.memory_container = QWidget()
        self.memory_container.setObjectName("memory_container")
        # NOTE: Removed WA_TranslucentBackground - was causing ghosting/smearing artifacts
        # when dragging widgets over this area. A solid background is needed for proper repaint.
        self.memory_layout = QVBoxLayout()
        self.memory_container.setLayout(self.memory_layout)
        scroll_area.setWidget(self.memory_container)
        
        layout.addWidget(scroll_area)
        
        self.empty_label = QLabel("暂无记忆\n对话中的关键信息将自动提取并显示在这里")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.setProperty("role", "empty_text")
        self.memory_layout.addWidget(self.empty_label)
        self.memory_layout.addStretch()
        
        self.setLayout(layout)
        self.setObjectName("memory_viewer")
    
    def update_memories(self, memories: List[Dict]):
        """Update displayed memories"""
        self.memories = memories
        self._refresh_display()
    
    def _refresh_display(self):
        """Refresh memory display"""
        # Clear existing memory cards - safely handle widget deletion
        while self.memory_layout.count():
            item = self.memory_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        
        # Reset empty_label reference since it was deleted above
        self.empty_label = None
        
        if not self.memories:
            # Create new empty label
            self.empty_label = QLabel("暂无记忆\n对话中的关键信息将自动提取并显示在这里")
            self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.empty_label.setProperty("role", "empty_text")
            self.memory_layout.addWidget(self.empty_label)
        else:
            # Add memory cards (no need to hide empty_label since it's already deleted)
            for memory in self.memories:
                card = self._create_memory_card(memory)
                self.memory_layout.addWidget(card)
        
        self.memory_layout.addStretch()
    
    def _create_memory_card(self, memory: Dict) -> QWidget:
        """Create a memory card widget"""
        card = QWidget()
        card.setProperty("role", "card")
        
        layout = QVBoxLayout()
        layout.setSpacing(5)
        
        category = memory.get('category', 'unknown')
        # Map categories to colors via property if possible, but for now we set inline style 
        # ONLY for the category badge mainly because of the dynamic nature of categories.
        # Alternatively, we can use qproperty-category and style in CSS.
        # Let's use property for category badge
        
        category_label = QLabel(f"📌 {category}")
        category_label.setProperty("role", "category_badge")
        category_label.setProperty("category", category)
        layout.addWidget(category_label)
        
        content_text = QTextEdit()
        content_text.setPlainText(memory.get('content', ''))
        content_text.setReadOnly(True)
        content_text.setMaximumHeight(80)
        content_text.setProperty("role", "card_content")
        layout.addWidget(content_text)
        
        # Timestamp
        if 'created_at' in memory:
            timestamp_label = QLabel(f"记录时间: {memory['created_at'][:19]}")
            timestamp_label.setProperty("role", "timestamp")
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

