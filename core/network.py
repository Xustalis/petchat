"""
Network Client for PetChat - Clean Client-Server Architecture
Manages TCP connection to the server and handles message routing.
"""
import socket
import threading
import json
import struct
import zlib
from typing import Optional, List
from PyQt6.QtCore import QObject, pyqtSignal


# Protocol constants
HEADER_SIZE = 8  # 4 bytes length + 4 bytes CRC32


def pack_message(data: dict) -> bytes:
    """Pack a message with length header and CRC32"""
    payload = json.dumps(data).encode('utf-8')
    length = len(payload)
    checksum = zlib.crc32(payload) & 0xFFFFFFFF
    header = struct.pack('>II', length, checksum)
    return header + payload


def unpack_header(header_bytes: bytes) -> tuple:
    """Unpack header to get (length, crc32)"""
    return struct.unpack('>II', header_bytes)


def verify_crc(payload: bytes, expected_crc: int) -> bool:
    """Verify CRC32 checksum"""
    return (zlib.crc32(payload) & 0xFFFFFFFF) == expected_crc


class NetworkManager(QObject):
    """
    Client-side network manager.
    Handles connection to server, sending and receiving messages.
    """
    
    # Connection signals
    connected = pyqtSignal()
    disconnected = pyqtSignal()
    connection_error = pyqtSignal(str)
    
    # Message signal: sender_id, sender_name, content, target, sender_avatar
    message_received = pyqtSignal(str, str, str, str, str)
    
    # User presence signals
    user_joined = pyqtSignal(str, str, str)  # user_id, user_name, avatar
    user_left = pyqtSignal(str)  # user_id
    online_users_received = pyqtSignal(list)  # list of user dicts
    
    # Typing signal
    typing_status_received = pyqtSignal(str, str, bool)  # user_id, user_name, is_typing

    def __init__(self):
        super().__init__()
        self.socket: Optional[socket.socket] = None
        self.running = False
        
        self.server_ip = "127.0.0.1"
        self.server_port = 8888
        
        self.user_id = ""
        self.user_name = ""
        self.avatar = ""
        
        self._send_lock = threading.Lock()
        self._recv_thread: Optional[threading.Thread] = None

    def connect_to_server(self, server_ip: str, port: int, user_id: str, user_name: str, avatar: str = ""):
        """Connect to the server and register"""
        self.server_ip = server_ip
        self.server_port = port
        self.user_id = user_id
        self.user_name = user_name
        self.avatar = avatar
        
        # Connect in background thread
        threading.Thread(target=self._connect_thread, daemon=True).start()

    def _connect_thread(self):
        """Background connection thread"""
        try:
            print(f"[Network] Connecting to {self.server_ip}:{self.server_port}...")
            
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(10.0)
            self.socket.connect((self.server_ip, self.server_port))
            self.socket.settimeout(None)
            
            self.running = True
            print("[Network] Connected!")
            
            # Register with server
            self._send_message({
                "type": "register",
                "user_id": self.user_id,
                "user_name": self.user_name,
                "avatar": self.avatar
            })
            
            self.connected.emit()
            
            # Start receive loop
            self._recv_thread = threading.Thread(target=self._receive_loop, daemon=True)
            self._recv_thread.start()
            
        except Exception as e:
            print(f"[Network] Connection failed: {e}")
            self.running = False
            self.connection_error.emit(str(e))

    def disconnect(self):
        """Disconnect from server"""
        self.running = False
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
            self.socket = None
        self.disconnected.emit()

    def stop(self):
        """Stop the network manager"""
        self.disconnect()

    def send_chat_message(self, target: str, content: str):
        """Send a chat message"""
        self._send_message({
            "type": "chat_message",
            "sender_id": self.user_id,
            "sender_name": self.user_name,
            "sender_avatar": self.avatar,
            "target": target,
            "content": content
        })

    def send_typing_status(self, is_typing: bool):
        """Send typing status"""
        self._send_message({
            "type": "typing_status",
            "sender_id": self.user_id,
            "sender_name": self.user_name,
            "is_typing": is_typing
        })

    def _send_message(self, message: dict):
        """Send a message to the server"""
        if not self.socket or not self.running:
            print("[Network] Cannot send - not connected")
            return
            
        try:
            with self._send_lock:
                packet = pack_message(message)
                self.socket.sendall(packet)
                print(f"[Network] Sent: {message.get('type')}")
        except Exception as e:
            print(f"[Network] Send error: {e}")
            self.disconnect()

    def _receive_loop(self):
        """Main receive loop"""
        print("[Network] Receive loop started")
        
        while self.running and self.socket:
            try:
                # Read header
                header = self._recv_exact(HEADER_SIZE)
                if not header:
                    print("[Network] Connection closed by server")
                    break
                
                length, expected_crc = unpack_header(header)
                
                # Read payload
                payload = self._recv_exact(length)
                if not payload:
                    print("[Network] Connection lost during payload read")
                    break
                
                # Verify CRC
                if not verify_crc(payload, expected_crc):
                    print("[Network] CRC mismatch, skipping message")
                    continue
                
                # Parse and handle message
                try:
                    message = json.loads(payload.decode('utf-8'))
                    self._handle_message(message)
                except json.JSONDecodeError:
                    print("[Network] Invalid JSON received")
                    
            except Exception as e:
                if self.running:
                    print(f"[Network] Receive error: {e}")
                break
        
        print("[Network] Receive loop ended")
        self.running = False
        self.disconnected.emit()

    def _recv_exact(self, n: int) -> Optional[bytes]:
        """Receive exactly n bytes"""
        data = b''
        while len(data) < n and self.running:
            try:
                chunk = self.socket.recv(n - len(data))
                if not chunk:
                    return None
                data += chunk
            except:
                return None
        return data if len(data) == n else None

    def _handle_message(self, message: dict):
        """Handle incoming message"""
        msg_type = message.get("type")
        print(f"[Network] Received: {msg_type}")
        
        if msg_type == "chat_message":
            self.message_received.emit(
                message.get("sender_id", ""),
                message.get("sender_name", "Unknown"),
                message.get("content", ""),
                message.get("target", "public"),
                message.get("sender_avatar", "")
            )
            
        elif msg_type == "user_joined":
            self.user_joined.emit(
                message.get("user_id", ""),
                message.get("user_name", "Unknown"),
                message.get("avatar", "")
            )
            
        elif msg_type == "user_left":
            self.user_left.emit(message.get("user_id", ""))
            
        elif msg_type == "online_users":
            users = message.get("users", [])
            self.online_users_received.emit(users)
            
        elif msg_type == "typing_status":
            sender_id = message.get("sender_id", "")
            if sender_id != self.user_id:  # Ignore own typing status
                self.typing_status_received.emit(
                    sender_id,
                    message.get("sender_name", "Someone"),
                    message.get("is_typing", False)
                )
