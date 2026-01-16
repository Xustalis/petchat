"""Pet widget for displaying emotion state with animations - Floating Overlay Version"""
from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout
from PyQt6.QtCore import Qt, QTimer, QPoint
from PyQt6.QtGui import QMouseEvent
from typing import Dict, Optional
from ui.theme import Theme


class PetWidget(QWidget):
    """Floating overlay widget displaying the emotion pet with drag support"""
    
    EMOTION_DESCRIPTIONS = {
        "neutral": "氛围平和",
        "happy": "氛围愉快",
        "tense": "氛围紧张",
        "negative": "氛围消极"
    }
    
    EMOTION_EMOJIS = {
        "neutral": "🐱",
        "happy": "😸",
        "tense": "🙀",
        "negative": "😿"
    }
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_emotion = "neutral"
        self.current_confidence = 1.0
        
        # Drag support
        self._drag_position: Optional[QPoint] = None
        self._is_dragging = False
        
        # Animation for bounce effect
        self._bounce_offset = 0
        self._bounce_direction = 1
        self._animation_timer = QTimer(self)
        self._animation_timer.timeout.connect(self._on_animation_tick)
        self._animation_timer.start(50)  # 20 FPS
        
        self._init_ui()
    
    def _init_ui(self):
        """Initialize UI components"""
        # Enable transparent background
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.FramelessWindowHint)
        
        # Set fixed size for the floating pet
        self.setFixedSize(160, 180)
        
        # Main layout
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(Theme.SPACING_SM)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Emoji label - the main pet display
        self.emoji_label = QLabel(self.EMOTION_EMOJIS["neutral"])
        self.emoji_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.emoji_label.setStyleSheet("""
            QLabel {
                font-size: 80px;
                background: transparent;
                border: none;
            }
        """)
        layout.addWidget(self.emoji_label)
        
        # Status label
        self.status_label = QLabel(self.EMOTION_DESCRIPTIONS["neutral"])
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet(f"""
            QLabel {{
                color: {Theme.TEXT_PRIMARY};
                font-size: {Theme.FONT_SIZE_SM}px;
                font-weight: 600;
                background-color: {Theme.BG_SURFACE};
                border: 1px solid {Theme.BG_BORDER};
                border-radius: 12px;
                padding: 6px 16px;
            }}
        """)
        layout.addWidget(self.status_label)
        
        self.setLayout(layout)
        
        # Set cursor to indicate draggable
        self.setCursor(Qt.CursorShape.OpenHandCursor)
    
    def _on_animation_tick(self):
        """Handle animation tick for subtle bounce effect"""
        if self.current_emotion == "happy":
            # Bounce animation for happy state
            self._bounce_offset += self._bounce_direction * 2
            if self._bounce_offset >= 6:
                self._bounce_direction = -1
            elif self._bounce_offset <= -6:
                self._bounce_direction = 1
            
            # Apply bounce to emoji label margin
            self.emoji_label.setStyleSheet(f"""
                QLabel {{
                    font-size: 80px;
                    background: transparent;
                    border: none;
                    margin-top: {-self._bounce_offset}px;
                }}
            """)
        else:
            # Reset bounce
            self._bounce_offset = 0
            self._bounce_direction = 1
            self.emoji_label.setStyleSheet("""
                QLabel {
                    font-size: 80px;
                    background: transparent;
                    border: none;
                }
            """)
    
    def update_emotion(self, emotion_scores: Dict[str, float]):
        """
        Update pet emotion based on emotion scores
        
        Args:
            emotion_scores: Dict with emotion types as keys and confidence scores as values
        """
        if not emotion_scores:
            return
        
        new_emotion = max(emotion_scores.items(), key=lambda x: x[1])[0]
        new_confidence = emotion_scores.get(new_emotion, 1.0)
        
        self.current_emotion = new_emotion
        self.current_confidence = new_confidence
        
        # Update emoji
        emoji = self.EMOTION_EMOJIS.get(self.current_emotion, "🐱")
        self.emoji_label.setText(emoji)
        
        # Update description
        description = self.EMOTION_DESCRIPTIONS.get(self.current_emotion, "氛围平和")
        self.status_label.setText(description)
    
    # ==================== Drag Support ====================
    
    def mousePressEvent(self, event: QMouseEvent):
        """Handle mouse press for drag start"""
        if event.button() == Qt.MouseButton.LeftButton:
            self._is_dragging = True
            self._drag_position = event.globalPosition().toPoint() - self.pos()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
        else:
            super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event: QMouseEvent):
        """Handle mouse move for dragging"""
        if self._is_dragging and self._drag_position is not None:
            new_pos = event.globalPosition().toPoint() - self._drag_position
            
            # Constrain to parent widget bounds
            if self.parent():
                parent_widget = self.parent()
                # Type check for QWidget methods
                if hasattr(parent_widget, 'width') and hasattr(parent_widget, 'height'):
                    max_x = parent_widget.width() - self.width()
                    max_y = parent_widget.height() - self.height()
                    new_pos.setX(max(0, min(new_pos.x(), max_x)))
                    new_pos.setY(max(0, min(new_pos.y(), max_y)))
            
            self.move(new_pos)
            event.accept()
        else:
            super().mouseMoveEvent(event)
    
    def mouseReleaseEvent(self, event: QMouseEvent):
        """Handle mouse release for drag end"""
        if event.button() == Qt.MouseButton.LeftButton:
            self._is_dragging = False
            self._drag_position = None
            self.setCursor(Qt.CursorShape.OpenHandCursor)
            event.accept()
        else:
            super().mouseReleaseEvent(event)
    
    def closeEvent(self, event):
        """Clean up resources"""
        self._animation_timer.stop()
        super().closeEvent(event)
