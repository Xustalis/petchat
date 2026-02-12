"""
Network Client for PetChat - Clean Client-Server Architecture
Manages TCP connection to the server and handles message routing.
Implements auto-reconnection and heartbeat.
"""
import socket
import threading
import json
import time
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from PyQt6.QtCore import QObject, pyqtSignal

# Use shared protocol module
from core.protocol import (
    Protocol, MessageType, HEADER_SIZE,
    pack_message, unpack_header, verify_crc,
    AIAnalysisRequest
)

logger = logging.getLogger(__name__)

class NetworkManager(QObject):
    """
    Client-side network manager.
    Handles connection to server, sending and receiving messages.
    """
    
    # Connection signals
    connected = pyqtSignal()
    disconnected = pyqtSignal()
    connection_error = pyqtSignal(str)
    reconnection_status = pyqtSignal(str) # Status message for UI
    
    # Message signal: sender_id, sender_name, content, target, sender_avatar
    message_received = pyqtSignal(str, str, str, str, str)
    
    # User presence signals
    user_joined = pyqtSignal(str, str, str)  # user_id, user_name, avatar
    user_left = pyqtSignal(str)  # user_id
    online_users_received = pyqtSignal(list)  # list of user dicts
    
    # Typing signal
    typing_status_received = pyqtSignal(str, str, bool)  # user_id, user_name, is_typing
    
    # AI signals - server sends AI results to client
    ai_suggestion_received = pyqtSignal(str, dict)  # conversation_id, suggestion dict
    ai_emotion_received = pyqtSignal(str, dict)  # conversation_id, emotion scores
    ai_memory_received = pyqtSignal(str, list)  # conversation_id, memories list

    def __init__(self):
        super().__init__()
        self.socket: Optional[socket.socket] = None
        self.running = False
        self.should_reconnect = False
        
        self.server_ip = "127.0.0.1"
        self.server_port = 8888
        
        self.user_id = ""
        self.user_name = ""
        self.avatar = ""
        
        self._send_lock = threading.Lock()
        
        # Heartbeat
        self.last_pong_time = 0.0
        self.HEARTBEAT_INTERVAL = 5.0
        self.HEARTBEAT_TIMEOUT = 15.0 # Allow latency

    def connect_to_server(self, server_ip: str, port: int, user_id: str, user_name: str, avatar: str = ""):
        """Initialize connection parameters and start manager"""
        self.server_ip = server_ip
        self.server_port = port
        self.user_id = user_id
        self.user_name = user_name
        self.avatar = avatar
        
        if self.should_reconnect:
            return  # Already trying
            
        self.should_reconnect = True
        threading.Thread(target=self._connection_manager, daemon=True).start()

    def _connection_manager(self):
        """Manages connection life-cycle and retries"""
        attempt = 0
        base_delay = 1.0
        max_delay = 30.0
        
        while self.should_reconnect:
            if self.socket:
                time.sleep(1)
                continue
                
            try:
                # Notify UI
                if attempt > 0:
                    self.reconnection_status.emit(f"Reconnecting... (Attempt {attempt})")
                
                self._connect_socket()
                
                # Connection Successful
                self.running = True
                attempt = 0
                self.connected.emit()
                self.reconnection_status.emit("Connected")
                
                # Start heartbeat thread
                heartbeat_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
                heartbeat_thread.start()
                
                # Run receive loop (blocks until disconnect)
                self._receive_loop()
                
            except Exception as e:
                print(f"[Network] Connection attempt failed: {e}")
                self.running = False
                self.socket = None
            
            # If we fall through here, we are disconnected
            self.disconnected.emit()
            
            if self.should_reconnect:
                attempt += 1
                delay = min(max_delay, base_delay * (1.5 ** (attempt - 1)))
                self.reconnection_status.emit(f"Disconnected. Retrying in {delay:.1f}s...")
                time.sleep(delay)

    def _connect_socket(self):
        """Perform single connection attempt"""
        print(f"[Network] Connecting to {self.server_ip}:{self.server_port}...")
        
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.settimeout(10.0)
        self.socket.connect((self.server_ip, self.server_port))
        self.socket.settimeout(None)
        
        # Register
        self._send_message_sync({
            "type": MessageType.REGISTER.value,
            "user_id": self.user_id,
            "user_name": self.user_name,
            "avatar": self.avatar
        })
        
        self.last_pong_time = time.time() # Reset heartbeat

    def disconnect(self):
        """Disconnect functionality triggered by user"""
        self.should_reconnect = False
        self.running = False
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
            self.socket = None
        self.disconnected.emit()
        self.reconnection_status.emit("Disconnected")

    def stop(self):
        """Stop network manager completely"""
        self.disconnect()

    def send_chat_message(self, target: str, content: str):
        self._send_message_async({
            "type": MessageType.CHAT_MESSAGE.value,
            "sender_id": self.user_id,
            "sender_name": self.user_name,
            "sender_avatar": self.avatar,
            "target": target,
            "content": content
        })

    def send_typing_status(self, is_typing: bool):
        self._send_message_async({
            "type": MessageType.TYPING_STATUS.value,
            "sender_avatar": self.avatar, # Fix for older expectations?
            "sender_id": self.user_id,
            "sender_name": self.user_name,
            "is_typing": is_typing
        })

    def send_ai_analysis_request(self, conversation_id: str, context_snapshot: List[Dict[str, Any]] = None):
        request = AIAnalysisRequest(
            conversation_id=conversation_id,
            sender_id=self.user_id,
            sender_name=self.user_name,
            context_snapshot=context_snapshot
        )
        size = len(json.dumps(request.to_dict(), ensure_ascii=False).encode("utf-8"))
        ts = datetime.utcnow().isoformat(timespec="seconds") + "Z"
        logger.info(f"[Network] AI request send: ts={ts} bytes={size} conv={conversation_id}")
        self._send_message_async(request.to_dict())

    def _send_message_async(self, message: dict):
        """Send message without blocking main thread excessively"""
        if not self.socket or not self.running:
            return
        # For simplicity in this architecture, we send directly. 
        # In high load, a queuing thread is better.
        threading.Thread(target=self._send_message_sync, args=(message,), daemon=True).start()

    def _send_message_sync(self, message: dict):
        """Send message synchronously"""
        if not self.socket: return
        try:
            with self._send_lock:
                packet = pack_message(message)
                self.socket.sendall(packet)
        except Exception as e:
            print(f"[Network] Send failed: {e}")
            # Let heartbeat or recv loop handle disconnect

    def _receive_loop(self):
        """Main receive loop (runs in connection manager thread)"""
        while self.running and self.socket:
            try:
                header = self._recv_exact(HEADER_SIZE)
                if not header: break
                
                length, expected_crc = unpack_header(header)
                payload = self._recv_exact(length)
                if not payload: break
                
                if not verify_crc(payload, expected_crc):
                    continue
                
                try:
                    message = json.loads(payload.decode('utf-8'))
                    self._handle_message(message)
                except json.JSONDecodeError:
                    continue
                    
            except Exception:
                break
        
        self.running = False
        # Do not emit disconnected here, manager does it

    def _recv_exact(self, n: int) -> Optional[bytes]:
        data = b''
        while len(data) < n and self.running and self.socket:
            try:
                # Use small timeout to allow checking self.running
                self.socket.settimeout(1.0) 
                chunk = self.socket.recv(n - len(data))
                if not chunk: return None
                data += chunk
            except socket.timeout:
                continue
            except:
                return None
        return data if len(data) == n else None

    def _heartbeat_loop(self):
        """Sends PING and checks for PONG timeout"""
        while self.running and self.socket:
            try:
                time.sleep(self.HEARTBEAT_INTERVAL)
                if not self.running: break
                
                # Check timeout
                if time.time() - self.last_pong_time > self.HEARTBEAT_TIMEOUT:
                    print("[Network] Heartbeat timeout!")
                    if self.socket:
                        try:
                            self.socket.close() # Force disconnect
                        except:
                            pass
                    break
                
                # Send PING
                self._send_message_sync({"type": MessageType.PING.value})
                
            except Exception:
                break

    def _handle_message(self, message: dict):
        msg_type = message.get("type")
        
        if msg_type == MessageType.PONG.value:
            self.last_pong_time = time.time()
            return

        elif msg_type == MessageType.CHAT_MESSAGE.value:
            self.message_received.emit(
                message.get("sender_id", ""),
                message.get("sender_name", "Unknown"),
                message.get("content", ""),
                message.get("target", "public"),
                message.get("sender_avatar", "")
            )
            
        elif msg_type == MessageType.USER_JOINED.value:
            self.user_joined.emit(
                message.get("user_id", ""),
                message.get("user_name", "Unknown"),
                message.get("avatar", "")
            )
            
        elif msg_type == MessageType.USER_LEFT.value:
            self.user_left.emit(message.get("user_id", ""))
            
        elif msg_type == MessageType.ONLINE_USERS.value:
            users = message.get("users", [])
            self.online_users_received.emit(users)
            
        elif msg_type == MessageType.TYPING_STATUS.value:
            sender_id = message.get("sender_id", "")
            if sender_id != self.user_id:
                self.typing_status_received.emit(
                    sender_id,
                    message.get("sender_name", "Someone"),
                    message.get("is_typing", False)
                )
        
        # AI message handlers
        elif msg_type == MessageType.AI_SUGGESTION.value:
            title = message.get("title")
            content = message.get("content")
            suggestion_type = message.get("suggestion_type", "suggestion")
            if not isinstance(title, str) or not title.strip() or not isinstance(content, str) or not content.strip():
                ts = datetime.utcnow().isoformat(timespec="seconds") + "Z"
                logger.error(f"[Network] Invalid AI suggestion: ts={ts} conv={message.get('conversation_id','')}")
                return
            size = len(json.dumps(message, ensure_ascii=False).encode("utf-8"))
            ts = datetime.utcnow().isoformat(timespec="seconds") + "Z"
            logger.info(f"[Network] AI suggestion recv: ts={ts} bytes={size} conv={message.get('conversation_id','')}")
            self.ai_suggestion_received.emit(
                message.get("conversation_id", ""),
                {
                    "title": title,
                    "content": content,
                    "type": suggestion_type
                }
            )
        
        elif msg_type == MessageType.AI_EMOTION.value:
            scores = message.get("scores", {})
            if not isinstance(scores, dict) or not scores:
                ts = datetime.utcnow().isoformat(timespec="seconds") + "Z"
                logger.error(f"[Network] Invalid AI emotion: ts={ts} conv={message.get('conversation_id','')}")
                return
            filtered = {k: float(v) for k, v in scores.items() if isinstance(v, (int, float))}
            if not filtered:
                ts = datetime.utcnow().isoformat(timespec="seconds") + "Z"
                logger.error(f"[Network] Empty AI emotion: ts={ts} conv={message.get('conversation_id','')}")
                return
            size = len(json.dumps(message, ensure_ascii=False).encode("utf-8"))
            ts = datetime.utcnow().isoformat(timespec="seconds") + "Z"
            logger.info(f"[Network] AI emotion recv: ts={ts} bytes={size} conv={message.get('conversation_id','')}")
            self.ai_emotion_received.emit(
                message.get("conversation_id", ""),
                filtered
            )
        
        elif msg_type == MessageType.AI_MEMORY.value:
            memories = message.get("memories", [])
            if not isinstance(memories, list):
                ts = datetime.utcnow().isoformat(timespec="seconds") + "Z"
                logger.error(f"[Network] Invalid AI memories: ts={ts} conv={message.get('conversation_id','')}")
                return
            cleaned = [m for m in memories if isinstance(m, dict) and m.get("content")]
            if not cleaned:
                ts = datetime.utcnow().isoformat(timespec="seconds") + "Z"
                logger.error(f"[Network] Empty AI memories: ts={ts} conv={message.get('conversation_id','')}")
                return
            size = len(json.dumps(message, ensure_ascii=False).encode("utf-8"))
            ts = datetime.utcnow().isoformat(timespec="seconds") + "Z"
            logger.info(f"[Network] AI memories recv: ts={ts} bytes={size} conv={message.get('conversation_id','')}")
            self.ai_memory_received.emit(
                message.get("conversation_id", ""),
                cleaned
            )
