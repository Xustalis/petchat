"""Main entry point for pet-chat application"""
import sys
import argparse
import socket
from PyQt6.QtWidgets import QApplication, QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QRadioButton, QButtonGroup, QMessageBox
from PyQt6.QtCore import Qt, QTimer

from core.network import NetworkManager
from core.database import Database
from core.ai_service import AIService
from core.config_manager import ConfigManager
from core.window_manager import window_manager
from ui.main_window import MainWindow
from ui.api_config_dialog import APIConfigDialog
from config.settings import Settings
from ui.theme import Theme


class RoleSelectionDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.selected_role = "host"
        self.host_ip = ""
        self.port_text = str(Settings.DEFAULT_PORT)
        self.setWindowTitle("选择启动模式")
        self.setModal(True)
        self.setMinimumWidth(420)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(Theme.SPACING_MD)
        self.setStyleSheet(Theme.get_stylesheet())

        title = QLabel("选择启动模式")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet(f"font-size: {Theme.FONT_SIZE_LG}px; font-weight: bold; color: {Theme.TEXT_PRIMARY};")
        layout.addWidget(title)
        
        hint = QLabel("请选择您的角色：房主负责创建房间，访客可以加入现有房间。")
        hint.setWordWrap(True)
        hint.setStyleSheet(f"color: {Theme.TEXT_SECONDARY}; font-size: {Theme.FONT_SIZE_SM}px;")
        layout.addWidget(hint)

        role_layout = QHBoxLayout()
        host_radio = QRadioButton("Host（房主）")
        guest_radio = QRadioButton("Guest（访客）")
        host_radio.setChecked(True)

        group = QButtonGroup(self)
        group.addButton(host_radio)
        group.addButton(guest_radio)

        role_layout.addWidget(host_radio)
        role_layout.addWidget(guest_radio)
        role_layout.addStretch()
        layout.addLayout(role_layout)

        ip_label = QLabel("Host IP（仅 Guest 需要填写）")
        self.ip_input = QLineEdit()
        self.ip_input.setPlaceholderText("例如 192.168.1.100")
        self.ip_input.setEnabled(False)

        layout.addWidget(ip_label)
        layout.addWidget(self.ip_input)

        port_label = QLabel("端口")
        self.port_input = QLineEdit(self.port_text)
        layout.addWidget(port_label)
        layout.addWidget(self.port_input)

        button_layout = QHBoxLayout()
        button_layout.addStretch()
        cancel_btn = QPushButton("取消")
        ok_btn = QPushButton("确定")
        
        # Style buttons explicitly
        cancel_btn.setStyleSheet(f"background-color: {Theme.SECONDARY}; color: white;")
        
        button_layout.addWidget(cancel_btn)
        button_layout.addWidget(ok_btn)
        layout.addLayout(button_layout)

        self.setLayout(layout)

        def on_host_selected(checked):
            if checked:
                self.selected_role = "host"
                self.ip_input.setEnabled(False)

        def on_guest_selected(checked):
            if checked:
                self.selected_role = "guest"
                self.ip_input.setEnabled(True)

        host_radio.toggled.connect(on_host_selected)
        guest_radio.toggled.connect(on_guest_selected)

        def on_ok():
            self.host_ip = self.ip_input.text().strip()
            self.port_text = self.port_input.text().strip() or str(Settings.DEFAULT_PORT)
            self.accept()

        def on_cancel():
            self.reject()

        ok_btn.clicked.connect(on_ok)
        cancel_btn.clicked.connect(on_cancel)


class PetChatApp:
    """Main application controller"""
    
    def __init__(self, is_host: bool, host_ip: str, port: int, from_cli_args: bool):
        print("[DEBUG] PetChatApp.__init__ starting...")
        
        # Create QApplication first, before any other PyQt6 operations
        print("[DEBUG] Creating QApplication...")
        self.app = QApplication(sys.argv)
        print("[DEBUG] QApplication created")
        
        # Apply global theme
        print("[DEBUG] Applying theme...")
        self.app.setStyleSheet(Theme.get_stylesheet())
        print("[DEBUG] Theme applied")
        
        self.is_host = is_host
        self.host_ip = host_ip
        self.port = port
        self.from_cli_args = from_cli_args
        print(f"[DEBUG] Configuration: is_host={is_host}, host_ip={host_ip}, port={port}, from_cli_args={from_cli_args}")
        
        print("[DEBUG] Creating ConfigManager...")
        self.config_manager = ConfigManager()
        print("[DEBUG] ConfigManager created")
        
        print("[DEBUG] Creating Database...")
        self.db = Database()
        print("[DEBUG] Database created")
        
        self.ai_service = None  # Only host has AI service
        
        print("[DEBUG] Creating MainWindow...")
        self.window = MainWindow(is_host=is_host)
        print("[DEBUG] MainWindow created")
        
        print("[DEBUG] Registering window...")
        self.window_id = window_manager().register_window(self.window)
        print(f"[DEBUG] Window registered with ID: {self.window_id}")
        
        self.app.aboutToQuit.connect(lambda: window_manager().unregister_window(self.window_id))
        self.message_count = 0
        print("[DEBUG] PetChatApp.__init__ completed")
    
    def _setup_connections(self):
        """Setup signal/slot connections"""
        # Network signals
        self.network.message_received.connect(self._on_message_received)
        self.network.connection_status_changed.connect(self._on_connection_status)
        self.network.error_occurred.connect(self._on_network_error)
        
        self.window.message_sent.connect(self._on_message_sent)
        self.window.ai_requested.connect(self._on_ai_requested)
        
        if self.is_host:
            self.window.api_config_changed.connect(self._on_api_config_applied)
            self.window.api_config_reset.connect(self._on_api_config_reset)
            self.window.memory_viewer.clear_requested.connect(self._on_clear_memories)
        
        # Update memories display periodically
        self._update_memories_display()
    
    def _on_connection_status(self, connected: bool, message: str):
        """Handle connection status changes"""
        self.window.update_status(message)
        if not connected:
            self.window.add_message("System", f"⚠️ 连接断开: {message}")

    def _on_network_error(self, error_msg: str):
        """Handle network errors"""
        self.window.update_status(f"Error: {error_msg}")
        # Optional: log error to console or file
        print(f"Network Error: {error_msg}")

    def _init_ai_service(self):
        """Initialize AI service with config"""
        if not self.is_host:
            return
        
        api_key = self.config_manager.get_api_key()
        if api_key:
            try:
                api_base = self.config_manager.get_api_base()
                self.ai_service = AIService(api_key=api_key, api_base=api_base)
            except Exception as e:
                self.window.show_suggestion({
                    "title": "AI服务初始化失败",
                    "content": f"无法初始化AI服务: {str(e)}\n请通过菜单栏配置API Key。"
                })
        else:
            # Show API config dialog on first run
            self._show_api_config_dialog()
    
    def _show_api_config_dialog(self):
        """Show API config dialog"""
        current_key = self.config_manager.get_api_key() or ""
        current_base = self.config_manager.get_api_base() or ""
        dialog = APIConfigDialog(current_key, current_base, self.window)
        dialog.config_applied.connect(self._on_api_config_applied)
        dialog.config_reset.connect(self._on_api_config_reset)
        dialog.exec()
    
    def _on_api_config_applied(self, api_key: str, api_base: str, persist: bool):
        if persist:
            self.config_manager.set_api_config(api_key, api_base)
        try:
            self.ai_service = AIService(api_key=api_key, api_base=api_base)
            QMessageBox.information(self.window, "配置已应用", "API配置已应用，AI功能已启用。")
        except Exception as e:
            QMessageBox.warning(self.window, "配置错误", f"无法初始化AI服务: {str(e)}")

    def _on_api_config_reset(self):
        self.config_manager.reset()
        self.ai_service = None
        QMessageBox.information(self.window, "配置已重置", "已清除所有API配置并恢复默认设置。")
    
    def _update_memories_display(self):
        """Update memories display in UI"""
        memories = self.db.get_memories()
        self.window.update_memories(memories)
    
    def _on_clear_memories(self):
        """Handle clear memories request"""
        self.db.clear_memories()
        self._update_memories_display()
    
    def _on_message_received(self, sender: str, content: str):
        """Handle received message"""
        # Add to database
        self.db.add_message(sender, content)
        
        # Add to UI
        self.window.add_message(sender, content)
        
        # Trigger AI analysis (host only)
        if self.is_host and self.ai_service:
            self.message_count += 1
            self._trigger_ai_analysis()
    
    def _on_message_sent(self, sender: str, content: str):
        """Handle sent message"""
        # Send via network
        self.network.send_message(sender, content)
        
        # Add to database
        self.db.add_message(sender, content)
        
        # Trigger AI analysis (host only)
        if self.is_host and self.ai_service:
            self.message_count += 1
            self._trigger_ai_analysis()
    
    def _trigger_ai_analysis(self):
        """Trigger AI analysis based on message count"""
        # Emotion analysis (every N messages)
        if self.message_count % Settings.EMOTION_ANALYSIS_INTERVAL == 0:
            self._analyze_emotion()
        
        # Memory extraction (every N messages)
        if self.message_count % Settings.MEMORY_EXTRACTION_INTERVAL == 0:
            self._extract_memories()
        
        # Suggestion check (every N messages)
        if self.message_count % Settings.SUGGESTION_CHECK_INTERVAL == 0:
            self._check_suggestions()
    
    def _analyze_emotion(self):
        """Analyze emotion from recent messages"""
        if not self.ai_service:
            return
        
        recent_messages = self.db.get_recent_messages(Settings.RECENT_MESSAGES_FOR_EMOTION)
        if len(recent_messages) < 2:
            return
        
        try:
            emotion_scores = self.ai_service.analyze_emotion(recent_messages)
            self.window.update_emotion(emotion_scores)
            
            # Store emotion in database
            emotion_type = max(emotion_scores.items(), key=lambda x: x[1])[0]
            confidence = emotion_scores[emotion_type]
            self.db.add_emotion(emotion_type, confidence)
        except Exception as e:
            print(f"Error analyzing emotion: {e}")
    
    def _extract_memories(self):
        """Extract memories from conversation"""
        if not self.ai_service:
            return
        
        recent_messages = self.db.get_recent_messages(20)
        if len(recent_messages) < 3:
            return
        
        try:
            memories = self.ai_service.extract_memories(recent_messages)
            for memory in memories:
                # Check if similar memory already exists
                existing = self.db.get_memories()
                # Simple duplicate check
                if memory['content'] not in [m['content'] for m in existing]:
                    self.db.add_memory(memory['content'], memory.get('category'))
            # Update UI
            self._update_memories_display()
        except Exception as e:
            print(f"Error extracting memories: {e}")
    
    def _check_suggestions(self):
        """Check if suggestion should be generated"""
        if not self.ai_service:
            return
        
        recent_messages = self.db.get_recent_messages(5)
        if len(recent_messages) < 2:
            return
        
        try:
            suggestion = self.ai_service.generate_suggestion(recent_messages)
            if suggestion:
                self.window.show_suggestion(suggestion)
        except Exception as e:
            print(f"Error generating suggestion: {e}")
    
    def _on_ai_requested(self):
        """Handle explicit AI request (/ai command)"""
        if not self.ai_service:
            self.window.show_suggestion({
                "title": "AI服务不可用",
                "content": "AI服务未初始化。请检查API Key配置。"
            })
            return
        
        recent_messages = self.db.get_recent_messages(10)
        if len(recent_messages) < 2:
            self.window.show_suggestion({
                "title": "信息不足",
                "content": "需要更多对话内容才能生成建议。"
            })
            return
        
        try:
            # Generate comprehensive suggestion
            suggestion = self.ai_service.generate_suggestion(recent_messages)
            if suggestion:
                self.window.show_suggestion(suggestion)
            else:
                # Try to extract memories as suggestion
                memories = self.ai_service.extract_memories(recent_messages)
                if memories:
                    memory_text = "\n".join([f"- {m['content']}" for m in memories[:3]])
                    self.window.show_suggestion({
                        "title": "对话要点",
                        "content": memory_text
                    })
                else:
                    self.window.show_suggestion({
                        "title": "暂无建议",
                        "content": "当前对话暂无可提取的建议。"
                    })
        except Exception as e:
            self.window.show_suggestion({
                "title": "AI处理错误",
                "content": f"处理请求时出错: {str(e)}"
            })
    
    def start(self):
        """Start the application"""
        if not self.from_cli_args:
            dialog = RoleSelectionDialog(self.window)
            result = dialog.exec()
            if result != QDialog.DialogCode.Accepted:
                return
            if dialog.selected_role == "host":
                self.is_host = True
                self.host_ip = Settings.DEFAULT_HOST_IP
            else:
                self.is_host = False
                self.host_ip = dialog.host_ip or Settings.DEFAULT_GUEST_IP
            try:
                self.port = int(dialog.port_text)
            except ValueError:
                self.port = Settings.DEFAULT_PORT
            self.window.is_host = self.is_host
            self.window.user_name = "Host" if self.is_host else "Guest"
            self.window.setWindowTitle(f"pet-chat - {self.window.user_name}")

        self.network = NetworkManager(is_host=self.is_host, host_ip=self.host_ip, port=self.port)
        self._setup_connections()

        if self.is_host:
            self._init_ai_service()

        if self.is_host:
            self.network.start_host()
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.connect(("8.8.8.8", 80))
                local_ip = s.getsockname()[0]
                s.close()
                self.window.update_status(f"Host模式 - 本地IP: {local_ip}, 端口: {self.port}")
            except:
                self.window.update_status(f"Host模式 - 端口: {self.port}")
        else:
            self.window.update_status("正在连接 Host...")
            self.network.connect_as_guest()
        
        # Show window
        print("[DEBUG] Showing window...")
        self.window.show()
        print("[DEBUG] Window shown")
        
        # Run application
        print("[DEBUG] Starting event loop...")
        result = self.app.exec()
        print(f"[DEBUG] Event loop exited with code: {result}")
        sys.exit(result)


def get_local_ip():
    """Get local IP address"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"


def main():
    """Main entry point"""
    print("Starting pet-chat application...")
    parser = argparse.ArgumentParser(description="pet-chat - AI-powered chat application")
    parser.add_argument("--host", action="store_true", help="Run as host (server)")
    parser.add_argument("--guest", action="store_true", help="Run as guest (client)")
    parser.add_argument("--host-ip", type=str, default=Settings.DEFAULT_GUEST_IP, 
                       help=f"Host IP address (default: {Settings.DEFAULT_GUEST_IP})")
    parser.add_argument("--port", type=int, default=Settings.DEFAULT_PORT,
                       help=f"Port number (default: {Settings.DEFAULT_PORT})")
    
    args = parser.parse_args()
    print(f"Parsed args: host={args.host}, guest={args.guest}, host_ip={args.host_ip}, port={args.port}")
    
    # Determine role
    is_host = args.host
    # If no role specified in CLI, we'll ask in GUI (unless pure CLI mode is desired, but here we have GUI)
    # The App controller handles the dialog if from_cli_args is False
    from_cli_args = args.host or args.guest
    print(f"Role: {'host' if is_host else 'guest'}, from_cli_args={from_cli_args}")
    
    print("Creating PetChatApp instance...")
    app = PetChatApp(is_host=is_host, host_ip=args.host_ip, port=args.port, from_cli_args=from_cli_args)
    print("PetChatApp instance created, starting application...")
    app.start()
    print("Application started")


if __name__ == "__main__":
    main()
