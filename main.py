import sys
import argparse
import socket
from PyQt6.QtWidgets import QApplication, QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QRadioButton, QButtonGroup, QMessageBox
from PyQt6.QtCore import Qt, QTimer, QObject
from core.network import NetworkManager
from core.database import Database
# Note: AIService removed - AI is now server-side only
from core.config_manager import ConfigManager
from core.window_manager import window_manager
from ui.main_window import MainWindow
from ui.user_profile_dialog import UserProfileDialog
# Note: APIConfigDialog removed - API config now on server
from config.settings import Settings
from ui.theme import Theme


class PetChatApp(QObject):
    """Main application controller"""
    
    def __init__(self, from_cli_args: bool = False, user_id: str = None, user_name: str = None):
        print("[DEBUG] PetChatApp.__init__ starting...")
        
        # Create QApplication first, before any other PyQt6 operations
        print("[DEBUG] Creating QApplication...")
        self.app = QApplication(sys.argv)
        print("[DEBUG] QApplication created")
        
        # CRITICAL: Call QObject's __init__ AFTER creating QApplication
        super().__init__()
        print("[DEBUG] QObject initialized")
        
        # Apply global theme
        print("[DEBUG] Applying theme...")
        self.app.setStyleSheet(Theme.get_stylesheet())
        print("[DEBUG] Theme applied")
        
        self.from_cli_args = from_cli_args
        self.server_ip = "127.0.0.1" # Default, will be updated from config
        self.server_port = 8888
        
        self.user_id_override = user_id
        self.user_name_override = user_name
        
        print(f"[DEBUG] Configuration: from_cli_args={from_cli_args}")
        
        print("[DEBUG] Creating ConfigManager...")
        self.config_manager = ConfigManager()
        print("[DEBUG] ConfigManager created")

        print("[DEBUG] Initializing user profile...")
        self.current_user_id, self.current_user_name, self.current_user_avatar = self._ensure_user_profile()
        print(f"[DEBUG] User profile: id={self.current_user_id}, name={self.current_user_name}, avatar={self.current_user_avatar}")
        
        print("[DEBUG] Creating Database...")
        self.db = Database()
        print("[DEBUG] Database created")
        
        # Register local user in database
        self.db.upsert_user(self.current_user_id, self.current_user_name, self.current_user_avatar, is_online=True)
        
        self.current_conversation_id = "default"
        self.loaded_message_limit = 50
        
        # Note: self.ai_service removed - AI is now server-side only
        self.discovery_service = None
        
        print("[DEBUG] Creating MainWindow...")
        self.window = MainWindow(user_id=self.current_user_id, user_name=self.current_user_name, user_avatar=self.current_user_avatar)
        print("[DEBUG] MainWindow created")
        
        print("[DEBUG] Registering window...")
        self.window_id = window_manager().register_window(self.window)
        print(f"[DEBUG] Window registered with ID: {self.window_id}")
        
        self.app.aboutToQuit.connect(lambda: window_manager().unregister_window(self.window_id))
        self.message_count = 0
        print("[DEBUG] PetChatApp.__init__ completed")
        self._load_messages(reset=True)
        self._load_conversations_list()

    def _ensure_user_profile(self):
        """Ensure user profile exists with persistent UUID"""
        # Checks overrides first
        if self.user_id_override and self.user_name_override:
             return self.user_id_override, self.user_name_override, "default_avatar"
             
        from core.models import generate_uuid
        
        # Get or generate user ID
        user_id = self.config_manager.get_user_id()
        if not user_id:
            user_id = generate_uuid()
            self.config_manager.set_user_id(user_id)
            print(f"[DEBUG] Generated new user ID: {user_id}")
        
        name = self.config_manager.get_user_name()
        avatar = self.config_manager.get_user_avatar()
        if name and 2 <= len(name.strip()) <= 20:
            return user_id, name.strip(), avatar or ""

        dialog = UserProfileDialog(current_name=name or "", current_avatar=avatar or "")
        result = dialog.exec()
        if result != QDialog.DialogCode.Accepted:
            sys.exit(0)
        final_name = dialog.user_name()
        final_avatar = dialog.avatar()
        self.config_manager.set_user_profile(final_name, final_avatar, user_id)
        return user_id, final_name, final_avatar

    def _load_messages(self, reset: bool = False):
        if reset:
            self.loaded_message_limit = 50
        try:
            messages = self.db.get_recent_messages(self.loaded_message_limit, conversation_id=self.current_conversation_id)
            self.window.clear_messages()
            for msg in messages:
                ts = msg.get("timestamp", "")
                display_ts = ts[11:16] if len(ts) >= 16 and ts[10] == "T" else ts[-5:]
                # Determine if this message is from me
                is_me = msg.get("sender_id") == self.current_user_id
                self.window.add_message(msg["sender"], msg["content"], display_ts, is_me=is_me)
        except Exception as e:
            print(f"Error loading message history: {e}")
    
    def _load_conversations_list(self):
        """Load conversations from database into sidebar"""
        try:
            conversations = self.db.get_conversations()
            self.window.load_conversations(conversations)
        except Exception as e:
            print(f"Error loading conversations: {e}")
    
    
    def _setup_connections(self):
        """Setup signal/slot connections"""
        # Network signals
        self.network.connected.connect(self._on_connected)
        self.network.disconnected.connect(self._on_disconnected)
        self.network.connection_error.connect(self._on_network_error)
        self.network.message_received.connect(self._on_message_received)
        self.network.user_joined.connect(self._on_user_joined)
        self.network.user_left.connect(self._on_user_left)
        self.network.online_users_received.connect(self._on_online_users_received)
        self.network.typing_status_received.connect(self._on_typing_status)
        
        # AI signals from server
        self.network.ai_suggestion_received.connect(self._on_server_ai_suggestion)
        self.network.ai_emotion_received.connect(self._on_server_ai_emotion)
        self.network.ai_memory_received.connect(self._on_server_ai_memory)
        
        # Window signals
        self.window.message_sent.connect(self._on_message_sent)
        self.window.ai_requested.connect(self._on_ai_requested)
        self.window.conversation_selected.connect(self._on_conversation_selected)
        self.window.load_more_requested.connect(self._on_load_more_requested)
        self.window.typing_changed.connect(self._on_local_typing_changed)
        self.window.reset_user_requested.connect(self._on_reset_user)
        self.window.user_selected.connect(self._on_user_selected_for_chat)
        
        # Note: api_config_changed and api_config_reset signals no longer connected
        # API configuration is now handled by the server
        self.window.memory_viewer.clear_requested.connect(self._on_clear_memories)
        
        # Update memories display
        self._update_memories_display()
    
    def _on_connected(self):
        """Handle successful connection"""
        self.window.update_status(f"已连接到服务器 {self.network.server_ip}")
        self.window.add_message("System", "✅ 已连接到服务器")
    
    def _on_disconnected(self):
        """Handle disconnection"""
        self.window.update_status("已断开连接")
        self.window.add_message("System", "⚠️ 与服务器断开连接")
    
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

    def _on_remote_suggestion(self, suggestion: dict):
        """Handle suggestion sent from peer"""
        self.window.show_suggestion(suggestion)

    def _on_conversation_selected(self, conversation_id: str):
        self.current_conversation_id = conversation_id or "default"
        self._load_messages(reset=True)
        # Clear AI panels when switching conversations
        self.window.clear_ai_panels()

    def _on_load_more_requested(self):
        self.loaded_message_limit += 50
        self._load_messages(reset=True)

    def _on_local_typing_changed(self, is_typing: bool):
        if self.network:
            self.network.send_typing_status(is_typing)
    
    def _on_user_joined(self, user_id: str, user_name: str, avatar: str):
        """Handle user joining"""
        print(f"[DEBUG] User joined: {user_name} ({user_id})")
        
        # Add/update user in database
        self.db.upsert_user(user_id, user_name, avatar, is_online=True)
        
        # Update UI online user list
        self._load_online_users()
        
        # Notification
        self.window.add_message("System", f"👋 {user_name} 加入了聊天")
    
    def _on_user_left(self, user_id: str):
        """Handle user leaving"""
        print(f"[DEBUG] User left: {user_id}")
        
        # Mark user as offline
        self.db.set_user_online_status(user_id, False)
        
        # Update UI
        self._load_online_users()
    
    def _load_online_users(self):
        """Load online users into sidebar"""
        try:
            users = self.db.get_all_users()
            online_users = [u for u in users if u.get("is_online") and u.get("id") != self.current_user_id]
            self.window.load_online_users(online_users)
            print(f"[DEBUG] Loaded {len(online_users)} online users to UI")
        except Exception as e:
            print(f"Error loading online users: {e}")
    
    def _on_online_users_received(self, users: list):
        """Handle online users list from server"""
        print(f"[DEBUG] Received online users list: {len(users)} users")
        for user in users:
            user_id = user.get("user_id")
            if user_id and user_id != self.current_user_id:
                self.db.upsert_user(
                    user_id, 
                    user.get("user_name", "Unknown"), 
                    user.get("avatar", ""),
                    is_online=True
                )
        self._load_online_users()
    
    def _on_user_selected_for_chat(self, peer_user_id: str, peer_user_name: str):
        """Handle user selection to start chat"""
        print(f"[DEBUG] User selected for chat: {peer_user_name} ({peer_user_id})")
        
        # Create or find private conversation
        # For now, we use the peer_user_id as the conversation_id for private chats
        # In a real app, this should be a unique UUID for the conversation
        conversation_id = peer_user_id 
        
        # Ensure conversation exists in DB
        self.db.get_or_create_conversation(conversation_id, "p2p", peer_user_name)
        
        # Switch to this conversation
        self.current_conversation_id = conversation_id
        
        # Reload conversations list in sidebar to show the new one
        self._load_conversations_list()
        
        # Select it in UI
        # TODO: Select the item in sidebar (requires mapping conversation_id to row)
        
        # Load messages for this conversation
        self._load_messages(reset=True)
        
        # Update window title or header?
        self.window.setWindowTitle(f"pet-chat - 与 {peer_user_name} 聊天中")
        
        # Show status message
        self.window.update_status(f"开始与 {peer_user_name} 的对话")
      
      
    def _on_remote_emotion(self, emotion_scores: dict):
        """Handle emotion scores sent from peer"""
        self.window.update_emotion(emotion_scores)

    def _on_remote_memories(self, memories: list):
        """Handle memories sent from peer"""
        self.window.update_memories(memories)

    # Note: _on_remote_ai_request removed as this client no longer hosts AI

    def _on_typing_status(self, user_id: str, sender_name: str, is_typing: bool):
        """Handle typing status from other users"""
        self.window.show_typing_status(sender_name, is_typing)

    # Note: _init_ai_service, _show_api_config_dialog, _on_api_config_applied, 
    # _on_api_config_reset removed as AI is server-side only.
    
    def _update_memories_display(self):
        """Update memories display in UI"""
        try:
            memories = self.db.get_memories()
            self.window.update_memories(memories)
        except RuntimeError as e:
            # Handle case where Qt widget has been deleted
            print(f"[WARN] Could not update memories display: {e}")
        except Exception as e:
            print(f"[ERROR] Error updating memories display: {e}")
    
    def _on_clear_memories(self):
        """Handle clear memories request"""
        self.db.clear_memories()
        self._update_memories_display()
        self.window.add_message("System", "📝 已清空所有记忆")
    
    def _on_reset_user(self):
        """Handle user reset request"""
        import os
        import sys
        from PyQt6.QtWidgets import QMessageBox
        
        try:
            print("[DEBUG] Starting user reset...")
            
            # Stop network services first
            if hasattr(self, 'network') and self.network:
                print("[DEBUG] Stopping network...")
                self.network.stop()
            
            if hasattr(self, 'discovery_service') and self.discovery_service:
                print("[DEBUG] Stopping discovery service...")
                self.discovery_service.stop()
            
            # Mark user as offline in database
            try:
                self.db.set_user_online_status(self.current_user_id, False)
                print("[DEBUG] Marked user as offline")
            except Exception as e:
                print(f"[WARN] Could not mark user offline: {e}")
            
            # Close database connection
            try:
                self.db.close()
                print("[DEBUG] Database closed")
            except Exception as e:
                print(f"[WARN] Could not close database: {e}")
            
            # Delete database file
            db_file = "petchat.db"
            try:
                if os.path.exists(db_file):
                    os.remove(db_file)
                    print(f"[DEBUG] Deleted database file: {db_file}")
            except Exception as e:
                print(f"[ERROR] Could not delete database: {e}")
            
            # Clear user data from config
            try:
                self.config_manager.config.pop('user_id', None)
                self.config_manager.config.pop('user_name', None)
                self.config_manager.config.pop('user_avatar', None)
                self.config_manager._save_config()
                print("[DEBUG] Cleared user data from config")
            except Exception as e:
                print(f"[ERROR] Could not clear config: {e}")
            
            # Show success message
            QMessageBox.information(
                self.window,
                "重置成功",
                "用户数据已清除。\n应用程序将关闭，请重新启动。"
            )
            
            # Close window and quit
            print("[DEBUG] Closing application...")
            self.app.quit()
            
        except Exception as e:
            print(f"[ERROR] Failed to reset user: {e}")
            self.window.add_message("System", f"❌ 重置用户失败: {e}")
    
    def _on_message_received(self, sender_id: str, sender_name: str, content: str, target: str, sender_avatar: str = ""):
        """Handle received message"""
        # Determine conversation ID
        if target == "public":
            conversation_id = "public"
            # Ensure public conversation exists (should always exist)
        else:
            # Private message: conversation with the sender
            conversation_id = sender_id
            # Ensure conversation exists
            self.db.get_or_create_conversation(conversation_id, "p2p", sender_name)
            
        target_conversation = conversation_id
        
        # Save to database
        self.db.add_message(sender_name, content, target_conversation, sender_id)
        
        # Update conversation last message
        self.db.update_conversation_last_message(target_conversation, content[:50])
        
        # If currently viewing this conversation, add to UI
        if target_conversation == self.current_conversation_id:
            self.window.add_message(sender_name, content, is_me=False, sender_avatar=sender_avatar)
        else:
            print(f"[DEBUG] Message received for conversation '{target_conversation}' but currently viewing '{self.current_conversation_id}'")
        
        # Trigger AI analysis (host only)
        # In CS mode, we don't trigger AI on every message locally.
        # Server handles analysis.
    
    def _on_message_sent(self, sender: str, content: str):
        """Handle sent message"""
        print(f"[DEBUG] _on_message_sent called: sender={sender}, content={content[:30]}")
        
        # Store with current user's ID
        self.db.add_message(sender, content, self.current_conversation_id, self.current_user_id)
        
        # Update conversation last message
        self.db.update_conversation_last_message(self.current_conversation_id, content[:50])
        
        # Send via network
        target = "public"
        if self.current_conversation_id != "public":
            target = self.current_conversation_id
        
        print(f"[DEBUG] Network status: network={self.network is not None}, running={self.network.running if self.network else 'N/A'}")
        
        if self.network:
            print(f"[DEBUG] Sending message to {target}: {content[:30]}")
            self.network.send_chat_message(target, content)
        else:
            print("[DEBUG] Network not available!")

        # Trigger auto-scroll if we were at the bottom
        # Note: AI analysis logic removed from here
    
    def _on_server_ai_suggestion(self, conversation_id: str, suggestion: dict):
        """Handle AI suggestion received from server"""
        # Only show if it matches current conversation or is global
        if conversation_id == self.current_conversation_id or not conversation_id:
            self.window.show_suggestion(suggestion)
            
    def _on_server_ai_emotion(self, conversation_id: str, emotion_scores: dict):
        """Handle AI emotion analysis received from server"""
        if conversation_id == self.current_conversation_id or not conversation_id:
            self.window.update_emotion(emotion_scores)
            
    def _on_server_ai_memory(self, conversation_id: str, memories: list):
        """Handle AI memories received from server"""
        # Save new memories to local DB
        if memories:
            for memory in memories:
                # Check for duplicates is handled by add_memory or we can check here
                # Using simple add for now, assuming server sends new valid memories
                # Ideally, add_memory should return success/fail or check duplicates
                self.db.add_memory(
                    content=memory.get('content', ''),
                    category=memory.get('category', 'general')
                )
            
            self.window.add_message("System", f"🧠 提取了 {len(memories)} 条新记忆")
            
        # Update UI from local DB
        self._update_memories_display() 

    def _on_ai_requested(self):
        """Handle explicit AI request (/ai command)"""
        if not self.network or not self.network.running:
             self.window.show_suggestion({
                "title": "未连接服务器",
                "content": "无法连接到服务器，无法请求 AI 建议。"
            })
             return

        # 1. Show loading state
        self.window.show_ai_loading()
        
        # 2. Collect context snapshot for cold-start recovery
        # (Recent 20 messages from current conversation)
        recent_messages = self.db.get_recent_messages(20)
        
        # 3. Send request to server
        self.network.send_ai_analysis_request(
            conversation_id=self.current_conversation_id,
            context_snapshot=recent_messages
        )
    
    
    def start(self):
        """Start the application"""
        # Initialize User ID first
        self.current_user_id, self.current_user_name, self.current_user_avatar = self._ensure_user_profile()
        
        # Determine server configuration
        if self.from_cli_args and self.server_ip:
            server_ip = self.server_ip
        else:
            server_ip = self.config_manager.config.get("server_ip", "127.0.0.1")
            
            # Ask for Server IP if not from CLI
            from PyQt6.QtWidgets import QInputDialog
            ip, ok = QInputDialog.getText(
                None, 
                "连接服务器", 
                "请输入服务器IP地址:", 
                text=server_ip
            )
            if ok and ip:
                server_ip = ip
                # Save to config
                self.config_manager.config["server_ip"] = server_ip
                self.config_manager.save_config()
            elif not ok:
                sys.exit(0)
            
        server_port = 8888
        
        # Create Network Manager
        self.network = NetworkManager()
        self._setup_connections()
        
        
        # Connect to Server (as Client)
        print(f"[DEBUG] Connecting to server at {server_ip}:{server_port}...")
        self.network.connect_to_server(
            server_ip, 
            server_port, 
            self.current_user_id, 
            self.current_user_name, 
            self.current_user_avatar
        )
        
        # Initial signals
        self.window.update_status(f"正在连接服务器 {server_ip}...")
        
        # Show window
        self.window.show()
        print("[DEBUG] Window shown")
        print("[DEBUG] Window shown")
        
        # Run application
        print("[DEBUG] Starting event loop...")
        result = self.app.exec()
        print(f"[DEBUG] Event loop exited with code: {result}")
        sys.exit(result)





def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Pet Chat Client")
    parser.add_argument("--server-ip", help="Server IP address to connect to automatically")
    parser.add_argument("--user-id", help="Override User ID", default=None)
    parser.add_argument("--user-name", help="Override User Name", default=None)
    args = parser.parse_args()
    
    print("Creating PetChatApp instance...")
    app = PetChatApp(
        from_cli_args=bool(args.server_ip),
        user_id=args.user_id,
        user_name=args.user_name
    )
    if args.server_ip:
        app.server_ip = args.server_ip
        
    print("PetChatApp instance created, starting application...")
    app.start()
    print("Application started")


if __name__ == "__main__":
    main()
