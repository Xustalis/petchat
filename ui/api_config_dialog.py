"""API Key configuration dialog"""
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                             QLineEdit, QPushButton, QTextEdit, QMessageBox,
                             QGroupBox, QFormLayout, QFileDialog, QCheckBox)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
import json


class APIConfigDialog(QDialog):
    """Dialog for configuring API settings"""
    
    config_applied = pyqtSignal(str, str, bool)
    config_reset = pyqtSignal()
    
    def __init__(self, current_api_key: str = "", current_api_base: str = "", parent=None):
        super().__init__(parent)
        self.setWindowTitle("API 配置")
        self.setModal(True)
        self.setMinimumWidth(520)
        self._init_ui(current_api_key, current_api_base)
    
    def _init_ui(self, current_api_key: str, current_api_base: str):
        """Initialize UI components"""
        layout = QVBoxLayout()
        layout.setSpacing(15)
        
        # Title
        title_label = QLabel("配置 AI API")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)
        
        # Info label
        info_label = QLabel(
            "pet-chat 使用 OpenAI API 兼容接口提供AI功能。\n"
            "请填写您的 API Key 和 API Base URL（可选）。"
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #666; padding: 10px;")
        layout.addWidget(info_label)
        
        # API Key input
        api_key_group = QGroupBox("API Key *")
        api_key_layout = QVBoxLayout()
        
        self.api_key_input = QLineEdit()
        self.api_key_input.setPlaceholderText("sk-...")
        self.api_key_input.setText(current_api_key)
        self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        api_key_layout.addWidget(self.api_key_input)
        
        # Show/Hide toggle
        show_key_btn = QPushButton("显示/隐藏")
        show_key_btn.setMaximumWidth(100)
        show_key_btn.clicked.connect(self._toggle_api_key_visibility)
        api_key_layout.addWidget(show_key_btn)
        
        api_key_group.setLayout(api_key_layout)
        layout.addWidget(api_key_group)
        
        api_base_group = QGroupBox("API Base URL (可选)")
        api_base_layout = QVBoxLayout()
        
        self.api_base_input = QLineEdit()
        self.api_base_input.setPlaceholderText("https://api.openai.com/v1")
        self.api_base_input.setText(current_api_base)
        api_base_layout.addWidget(self.api_base_input)
        
        info_text = QLabel("留空则使用默认 OpenAI API")
        info_text.setStyleSheet("color: #999; font-size: 11px;")
        api_base_layout.addWidget(info_text)
        
        api_base_group.setLayout(api_base_layout)
        layout.addWidget(api_base_group)

        remember_layout = QHBoxLayout()
        self.remember_checkbox = QCheckBox("记住配置")
        self.remember_checkbox.setChecked(True)
        remember_hint = QLabel("未勾选时，API Key 仅在本次运行中有效。")
        remember_hint.setStyleSheet("color: #6b7280; font-size: 11px;")
        remember_layout.addWidget(self.remember_checkbox)
        remember_layout.addWidget(remember_hint)
        remember_layout.addStretch()
        layout.addLayout(remember_layout)
        
        button_layout = QHBoxLayout()
        
        reset_btn = QPushButton("重置")
        reset_btn.clicked.connect(self._on_reset_clicked)
        button_layout.addWidget(reset_btn)

        import_btn = QPushButton("导入")
        import_btn.clicked.connect(self._import_config)
        button_layout.addWidget(import_btn)

        export_btn = QPushButton("导出")
        export_btn.clicked.connect(self._export_config)
        button_layout.addWidget(export_btn)

        button_layout.addStretch()
        
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        apply_btn = QPushButton("应用")
        apply_btn.clicked.connect(self._on_apply_clicked)
        button_layout.addWidget(apply_btn)
        
        save_btn = QPushButton("保存")
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 8px 20px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """)
        save_btn.clicked.connect(self._on_save_clicked)
        button_layout.addWidget(save_btn)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        self.setStyleSheet("""
            QDialog {
                background-color: #fafafa;
            }
            QGroupBox {
                font-weight: bold;
                border: 2px solid #ddd;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
            QLineEdit {
                padding: 8px;
                border: 1px solid #ddd;
                border-radius: 4px;
                font-size: 14px;
            }
            QLineEdit:focus {
                border: 2px solid #3498db;
            }
        """)
    
    def _toggle_api_key_visibility(self):
        """Toggle API key visibility"""
        if self.api_key_input.echoMode() == QLineEdit.EchoMode.Password:
            self.api_key_input.setEchoMode(QLineEdit.EchoMode.Normal)
        else:
            self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
    
    def _apply_config(self, persist: bool):
        api_key = self.api_key_input.text().strip()
        api_base = self.api_base_input.text().strip()
        
        if not api_key:
            QMessageBox.warning(self, "配置错误", "API Key 不能为空。")
            return
        
        if not api_key.startswith(('sk-', 'sk_')) and len(api_key) < 10:
            reply = QMessageBox.question(
                self,
                "确认",
                "API Key 格式可能不正确，是否继续？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.No:
                return
        
        self.config_applied.emit(api_key, api_base, persist)
        self.accept()

    def _on_apply_clicked(self):
        persist = self.remember_checkbox.isChecked()
        self._apply_config(persist)

    def _on_save_clicked(self):
        self.remember_checkbox.setChecked(True)
        self._apply_config(True)

    def _on_reset_clicked(self):
        reply = QMessageBox.question(
            self,
            "确认重置",
            "确定要清除所有API配置并恢复默认设置吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.config_reset.emit()
            self.api_key_input.clear()
            self.api_base_input.clear()

    def _import_config(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "导入配置",
            "",
            "JSON 文件 (*.json);;所有文件 (*.*)"
        )
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            api_key = data.get("api_key", "")
            api_base = data.get("api_base", "")
            self.api_key_input.setText(api_key)
            self.api_base_input.setText(api_base)
        except Exception as e:
            QMessageBox.warning(self, "导入失败", f"无法导入配置: {e}")

    def _export_config(self):
        api_key = self.api_key_input.text().strip()
        api_base = self.api_base_input.text().strip()
        if not api_key:
            QMessageBox.warning(self, "导出失败", "当前没有可导出的 API Key。")
            return
        path, _ = QFileDialog.getSaveFileName(
            self,
            "导出配置",
            "api_config.json",
            "JSON 文件 (*.json);;所有文件 (*.*)"
        )
        if not path:
            return
        try:
            data = {"api_key": api_key, "api_base": api_base}
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            QMessageBox.warning(self, "导出失败", f"无法导出配置: {e}")

