"""Suggestion panel for displaying AI-generated suggestions"""
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QTextEdit, QScrollArea
from PyQt6.QtCore import Qt, pyqtSignal
from typing import Optional, Dict
from ui.theme import Theme


class SuggestionPanel(QWidget):
    """Panel for displaying AI suggestions"""
    
    suggestion_adopted = pyqtSignal(str)  # Emitted when user adopts a suggestion
    
    def __init__(self, parent=None):    
        super().__init__(parent)
        self.current_suggestion: Optional[Dict] = None
        self._init_ui()
    
    def _init_ui(self):
        """Initialize UI components"""
        layout = QVBoxLayout()
        layout.setSpacing(10)
        
        title_label = QLabel("💡 AI 建议")
        title_label.setStyleSheet(
            f"font-weight: bold; font-size: 15px; color: {Theme.TEXT_PRIMARY};"
        )
        layout.addWidget(title_label)
        
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet(
            f"QScrollArea {{ border: 1px solid {Theme.BG_BORDER}; border-radius: {Theme.RADIUS_MD}px;"
            f" background-color: {Theme.BG_MUTED}; }}"
        )
        
        self.suggestion_container = QWidget()
        self.suggestion_layout = QVBoxLayout()
        self.suggestion_container.setLayout(self.suggestion_layout)
        scroll_area.setWidget(self.suggestion_container)
        
        layout.addWidget(scroll_area)
        
        self.setLayout(layout)
        self.setStyleSheet(
            f"QWidget {{ background-color: {Theme.BG_MAIN}; padding: 10px; }}"
        )
    
    def show_suggestion(self, suggestion: Dict):
        """
        Display a new suggestion
        
        Args:
            suggestion: Dict with 'title', 'content', and optionally 'type'
        """
        self.current_suggestion = suggestion
        
        # Clear existing suggestions
        self._clear_suggestions()
        
        card = QWidget()
        card_layout = QVBoxLayout()
        card_layout.setSpacing(8)
        
        title_label = QLabel(suggestion.get('title', '建议'))
        title_label.setStyleSheet(
            f"font-weight: bold; font-size: 13px; color: {Theme.TEXT_PRIMARY};"
        )
        card_layout.addWidget(title_label)
        
        content_text = QTextEdit()
        content_text.setPlainText(suggestion.get('content', ''))
        content_text.setReadOnly(True)
        content_text.setMaximumHeight(150)
        content_text.setStyleSheet(
            f"QTextEdit {{ border: 1px solid {Theme.BG_BORDER}; border-radius: {Theme.RADIUS_SM}px;"
            f" padding: 6px; background-color: {Theme.BG_MAIN}; color: {Theme.TEXT_PRIMARY}; font-size: 14px; }}"
        )
        card_layout.addWidget(content_text)
        
        adopt_btn = QPushButton("采用建议")
        adopt_btn.setStyleSheet(
            f"QPushButton {{ background-color: {Theme.PRIMARY}; color: {Theme.PRIMARY_TEXT};"
            f" border: none; border-radius: {Theme.RADIUS_SM}px; padding: 8px; font-weight: bold; }}"
            f" QPushButton:hover {{ background-color: {Theme.PRIMARY_HOVER}; }}"
        )
        adopt_btn.clicked.connect(lambda: self._on_adopt(suggestion.get('content', '')))
        card_layout.addWidget(adopt_btn)
        
        card.setLayout(card_layout)
        card.setStyleSheet(
            f"QWidget {{ background-color: {Theme.BG_MUTED}; border: 1px solid {Theme.BG_BORDER};"
            f" border-radius: {Theme.RADIUS_MD}px; padding: 10px; margin: 5px; }}"
        )
        
        self.suggestion_layout.addWidget(card)
        self.suggestion_layout.addStretch()
    
    def _clear_suggestions(self):
        """Clear all suggestion cards"""
        while self.suggestion_layout.count():
            item = self.suggestion_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
    
    def clear(self):
        """Clear all suggestions"""
        self.current_suggestion = None
        self._clear_suggestions()
    
    def _on_adopt(self, content: str):
        """Handle adopt button click"""
        self.suggestion_adopted.emit(content)
        # Optionally hide after adopting
        # self.clear()

