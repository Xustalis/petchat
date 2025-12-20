"""Pet widget for displaying emotion state with animations"""
from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout
from PyQt6.QtCore import Qt, QTimer, QPointF
from PyQt6.QtGui import QPainter, QBrush, QPen, QRadialGradient, QColor
from typing import Dict
from ui.theme import Theme


class PetWidget(QWidget):
    """Widget displaying the emotion pet with animations"""
    
    EMOTION_DESCRIPTIONS = {
        "neutral": "氛围平和",
        "happy": "氛围愉快",
        "tense": "氛围紧张",
        "negative": "氛围消极"
    }
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_emotion = "neutral"
        self.current_confidence = 1.0
        self.blink_state = False
        
        # Animation setup
        self.animation_timer = QTimer(self)
        self.animation_timer.timeout.connect(self._on_animation_tick)
        self.start_animation()
        
        self._init_ui()
    
    def _init_ui(self):
        """Initialize UI components"""
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(Theme.SPACING_SM)

        self.status_label = QLabel(self.EMOTION_DESCRIPTIONS["neutral"])
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet(f"color: {Theme.TEXT_SECONDARY}; font-size: {Theme.FONT_SIZE_SM}px; font-weight: 500;")
        layout.addWidget(self.status_label)
        
        self.setLayout(layout)
        # Use Theme colors for background
        self.setStyleSheet(f"""
            QWidget {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {Theme.BG_HOVER}, stop:1 {Theme.BG_SELECTED});
                border-radius: {Theme.RADIUS_LG}px;
                padding: {Theme.SPACING_MD}px;
                border: 2px solid {Theme.BG_SELECTED};
            }}
        """)
        self.setMinimumHeight(180)
    
    def start_animation(self, interval: int = 800):
        """Start the animation loop"""
        self.animation_timer.start(interval)
        
    def stop_animation(self):
        """Stop the animation loop"""
        self.animation_timer.stop()
        
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
        
        emotion_changed = new_emotion != self.current_emotion
        self.current_emotion = new_emotion
        self.current_confidence = new_confidence
        
        description = self.EMOTION_DESCRIPTIONS.get(self.current_emotion, "氛围平和")
        self.status_label.setText(description)
        
        if emotion_changed:
            self.blink_state = False
        self.update()

    def _on_animation_tick(self):
        """Handle animation tick"""
        self._update_blink_state()
        self.update()

    def _update_blink_state(self):
        """Toggle blink state"""
        self.blink_state = not self.blink_state

    def closeEvent(self, event):
        """Clean up resources"""
        self.stop_animation()
        super().closeEvent(event)

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        width = self.width()
        height = self.height()

        center_x = width // 2
        center_y = height // 2 - 10

        # Draw shadow
        self._draw_shadow(painter, center_x, center_y)
        
        # Determine base color
        base_color = self._get_emotion_color()

        # Draw body
        self._draw_body(painter, center_x, center_y, base_color)

        # Draw ears
        self._draw_ears(painter, center_x, center_y, base_color)

        # Draw eyes
        self._draw_eyes(painter, center_x, center_y)

        # Draw mouth
        self._draw_mouth(painter, center_x, center_y)

        # Draw whiskers
        self._draw_whiskers(painter, center_x, center_y)

    def _draw_shadow(self, painter, cx, cy):
        shadow_radius = 60
        shadow_color = QColor(0, 0, 0, 40)
        painter.setBrush(QBrush(shadow_color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(cx - shadow_radius, cy + 55, shadow_radius * 2, 16)

    def _get_emotion_color(self):
        if self.current_emotion == "happy":
            return QColor("#34d399")
        elif self.current_emotion == "tense":
            return QColor("#fbbf24")
        elif self.current_emotion == "negative":
            return QColor("#fb7185")
        else:
            return QColor("#9ca3af")

    def _draw_body(self, painter, cx, cy, color):
        body_radius = 55
        gradient = QRadialGradient(cx - 20, cy - 40, body_radius * 1.4)
        gradient.setColorAt(0.0, QColor(255, 255, 255))
        gradient.setColorAt(0.4, color.lighter(120))
        gradient.setColorAt(1.0, color.darker(130))

        painter.setBrush(QBrush(gradient))
        painter.setPen(QPen(QColor(255, 255, 255, 180), 2))
        painter.drawEllipse(cx - body_radius, cy - body_radius, body_radius * 2, body_radius * 2)

    def _draw_ears(self, painter, cx, cy, color):
        body_radius = 55
        ear_height = 26
        ear_width = 26
        ear_color = color.darker(110)
        painter.setBrush(QBrush(ear_color))
        painter.setPen(QPen(QColor(255, 255, 255, 160), 2))
        
        left_ear = [
            (cx - body_radius + 18, cy - body_radius + 4),
            (cx - body_radius + 18 + ear_width, cy - body_radius + 4),
            (cx - body_radius + 18 + ear_width // 2, cy - body_radius - ear_height),
        ]
        right_ear = [
            (cx + body_radius - 18 - ear_width, cy - body_radius + 4),
            (cx + body_radius - 18, cy - body_radius + 4),
            (cx + body_radius - 18 - ear_width // 2, cy - body_radius - ear_height),
        ]
        painter.drawPolygon(*[QPointF(x, y) for x, y in left_ear])
        painter.drawPolygon(*[QPointF(x, y) for x, y in right_ear])

    def _draw_eyes(self, painter, cx, cy):
        eye_radius = 6
        eye_offset_x = 18
        eye_offset_y = 8
        eye_color = QColor(30, 41, 59)

        if self.blink_state:
            painter.setPen(QPen(eye_color, 2))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawLine(cx - eye_offset_x - eye_radius, cy - eye_offset_y,
                             cx - eye_offset_x + eye_radius, cy - eye_offset_y)
            painter.drawLine(cx + eye_offset_x - eye_radius, cy - eye_offset_y,
                             cx + eye_offset_x + eye_radius, cy - eye_offset_y)
        else:
            painter.setBrush(QBrush(eye_color))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(cx - eye_offset_x - eye_radius, cy - eye_offset_y - eye_radius,
                                eye_radius * 2, eye_radius * 2)
            painter.drawEllipse(cx + eye_offset_x - eye_radius, cy - eye_offset_y - eye_radius,
                                eye_radius * 2, eye_radius * 2)

    def _draw_mouth(self, painter, cx, cy):
        mouth_width = 18
        mouth_height = 10
        mouth_y = cy + 10
        mouth_pen = QPen(QColor(30, 41, 59), 2)
        painter.setPen(mouth_pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)

        if self.current_emotion == "happy":
            painter.drawArc(cx - mouth_width // 2, mouth_y - mouth_height // 2,
                            mouth_width, mouth_height, 0, -180 * 16)
        elif self.current_emotion == "negative":
            painter.drawArc(cx - mouth_width // 2, mouth_y,
                            mouth_width, mouth_height, 0, 180 * 16)
        else:
            painter.drawLine(cx - mouth_width // 3, mouth_y,
                             cx + mouth_width // 3, mouth_y)

    def _draw_whiskers(self, painter, cx, cy):
        whisker_pen = QPen(QColor(75, 85, 99), 1.4)
        painter.setPen(whisker_pen)
        whisker_y = cy + 4
        painter.drawLine(cx - 8, whisker_y, cx - 32, whisker_y - 4)
        painter.drawLine(cx - 8, whisker_y + 4, cx - 32, whisker_y + 2)
        painter.drawLine(cx + 8, whisker_y, cx + 32, whisker_y - 4)
        painter.drawLine(cx + 8, whisker_y + 4, cx + 32, whisker_y + 2)
