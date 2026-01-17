"""P2P network communication module with thread-safe signals"""
import socket
import threading
import json
import time
from typing import Optional, Dict
from datetime import datetime
from PyQt6.QtCore import QObject, pyqtSignal, QMutex, QMutexLocker


class UDPDiscovery(QObject):
    """UDP broadcast-based user discovery for LAN mode"""
    
    user_discovered = pyqtSignal(dict)  # Emits user info: {id, name, ip, port}
    user_left = pyqtSignal(str)  # Emits user_id when user goes offline
    
    def __init__(self, user_id: str, user_name: str, tcp_port: int, broadcast_port: int = 8889):
        super().__init__()
        self.user_id = user_id
        self.user_name = user_name
        self.tcp_port = tcp_port
        self.broadcast_port = broadcast_port
        
        self.running = False
        self._broadcast_socket: Optional[socket.socket] = None
        self._listen_socket: Optional[socket.socket] = None
        self._broadcast_thread: Optional[threading.Thread] = None
        self._listen_thread: Optional[threading.Thread] = None
        
        # Track discovered users: {user_id: {name, ip, port, last_seen}}
        self._discovered_users: Dict[str, Dict] = {}
        self._mutex = QMutex()
    
    def start(self):
        """Start discovery service"""
        if self.running:
            return
        
        self.running = True
        
        # Start broadcast thread (announce presence)
        self._broadcast_thread = threading.Thread(target=self._broadcast_loop, daemon=True)
        self._broadcast_thread.start()
        
        # Start listen thread (discover others)
        self._listen_thread = threading.Thread(target=self._listen_loop, daemon=True)
        self._listen_thread.start()
    
    def stop(self):
        """Stop discovery service"""
        self.running = False
        
        # Send goodbye message
        self._send_goodbye()
        
        try:
            if self._broadcast_socket:
                self._broadcast_socket.close()
            if self._listen_socket:
                self._listen_socket.close()
        except Exception:
            pass
    
    def _broadcast_loop(self):
        """Periodically broadcast presence to LAN"""
        try:
            self._broadcast_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self._broadcast_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            
            while self.running:
                try:
                    message = json.dumps({
                        "type": "presence",
                        "user_id": self.user_id,
                        "user_name": self.user_name,
                        "tcp_port": self.tcp_port,
                        "timestamp": datetime.now().isoformat()
                    }).encode('utf-8')
                    
                    # Broadcast to entire subnet
                    self._broadcast_socket.sendto(message, ('<broadcast>', self.broadcast_port))
                    
                except Exception as e:
                    print(f"[UDP] Broadcast error: {e}")
                
                time.sleep(5.0)  # Announce every 5 seconds
                
        except Exception as e:
            print(f"[UDP] Failed to create broadcast socket: {e}")
    
    def _listen_loop(self):
        """Listen for presence announcements from other users"""
        try:
            self._listen_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self._listen_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self._listen_socket.bind(('', self.broadcast_port))
            self._listen_socket.settimeout(1.0)
            
            while self.running:
                try:
                    data, addr = self._listen_socket.recvfrom(4096)
                    message = json.loads(data.decode('utf-8'))
                    
                    msg_type = message.get("type")
                    user_id = message.get("user_id")
                    
                    # Ignore our own broadcasts
                    if user_id == self.user_id:
                        continue
                    
                    if msg_type == "presence":
                        self._handle_presence(message, addr[0])
                    elif msg_type == "goodbye":
                        self._handle_goodbye(user_id)
                        
                except socket.timeout:
                    # Check for stale users
                    self._check_stale_users()
                    continue
                except Exception as e:
                    if self.running:
                        print(f"[UDP] Listen error: {e}")
                    
        except Exception as e:
            print(f"[UDP] Failed to create listen socket: {e}")
    
    def _handle_presence(self, message: dict, ip_address: str):
        """Handle presence announcement from another user"""
        user_id = message.get("user_id")
        user_name = message.get("user_name")
        tcp_port = message.get("tcp_port")
        
        if not all([user_id, user_name, tcp_port]):
            return
        
        with QMutexLocker(self._mutex):
            is_new = user_id not in self._discovered_users
            
            self._discovered_users[user_id] = {
                "id": user_id,
                "name": user_name,
                "ip": ip_address,
                "port": tcp_port,
                "last_seen": time.time()
            }
        
        # Emit signal for new user
        if is_new:
            self.user_discovered.emit({
                "id": user_id,
                "name": user_name,
                "ip": ip_address,
                "port": tcp_port
            })
    
    def _handle_goodbye(self, user_id: str):
        """Handle user leaving"""
        with QMutexLocker(self._mutex):
            if user_id in self._discovered_users:
                del self._discovered_users[user_id]
                self.user_left.emit(user_id)
    
    def _check_stale_users(self):
        """Remove users that haven't been seen recently"""
        timeout = 15.0  # Remove if not seen for 15 seconds
        current_time = time.time()
        
        with QMutexLocker(self._mutex):
            stale_users = [
                user_id for user_id, info in self._discovered_users.items()
                if current_time - info["last_seen"] > timeout
            ]
            
            for user_id in stale_users:
                del self._discovered_users[user_id]
                self.user_left.emit(user_id)
    
    def _send_goodbye(self):
        """Send goodbye message before stopping"""
        try:
            if self._broadcast_socket:
                message = json.dumps({
                    "type": "goodbye",
                    "user_id": self.user_id
                }).encode('utf-8')
                self._broadcast_socket.sendto(message, ('<broadcast>', self.broadcast_port))
        except Exception:
            pass
    
    def get_discovered_users(self) -> list:
        """Get list of currently discovered users"""
        with QMutexLocker(self._mutex):
            return list(self._discovered_users.values())


class NetworkManager(QObject):
    """
    Manages P2P communication between Host and Guest.
    Thread-safe implementation using PyQt signals.
    """
    
    message_received = pyqtSignal(str, str)
    connection_status_changed = pyqtSignal(bool, str)
    error_occurred = pyqtSignal(str)
    ai_suggestion_received = pyqtSignal(dict)
    ai_emotion_received = pyqtSignal(dict)
    ai_memories_received = pyqtSignal(list)
    ai_request_received = pyqtSignal()
    typing_status_changed = pyqtSignal(bool)
    
    def __init__(self, is_host: bool = False, host_ip: str = "127.0.0.1", port: int = 8888,
                 use_relay: bool = False, relay_host: str = "", relay_port: int = 0, room_id: str = "default"):
        super().__init__()
        self.is_host = is_host
        self.host_ip = host_ip
        self.port = port
        self.use_relay = use_relay
        self.relay_host = relay_host or host_ip
        self.relay_port = relay_port or port
        self.room_id = room_id
        self._relay_role = "host" if is_host else "guest"
        
        self.socket: Optional[socket.socket] = None
        self.client_socket: Optional[socket.socket] = None
        
        self.running = False
        self._mutex = QMutex()
        self._reconnect_thread: Optional[threading.Thread] = None
        self._reconnect_active = False
        self._reconnect_delay_base = 1.0
        self._reconnect_delay_max = 30.0
        
        # Heartbeat settings
        self.last_heartbeat = 0
        self.heartbeat_interval = 5.0
        self.heartbeat_timeout = 15.0
        self._heartbeat_thread: Optional[threading.Thread] = None

    def start_host(self):
        """Start as host (server)"""
        if self.use_relay:
            self._start_relay(role="host")
            return
        if not self.is_host:
            self.error_occurred.emit("Cannot start as host when initialized as guest")
            return
        
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.socket.bind((self.host_ip, self.port))
            self.socket.listen(1)
            self.running = True
            
            self.connection_status_changed.emit(True, f"Host started on {self.host_ip}:{self.port}")
            
            # Accept connection in separate thread
            accept_thread = threading.Thread(target=self._accept_connection, daemon=True)
            accept_thread.start()
            
        except Exception as e:
            self.running = False
            self.error_occurred.emit(f"Failed to start host: {str(e)}")

    def _accept_connection(self):
        """Accept incoming connection (host only)"""
        try:
            if not self.socket:
                return
                
            self.client_socket, addr = self.socket.accept()
            
            # Notify UI
            self.connection_status_changed.emit(True, f"Guest connected from {addr[0]}")
            
            # Start receiving messages
            self._start_io_threads(self.client_socket)
            
        except Exception as e:
            if self.running:
                self.error_occurred.emit(f"Error accepting connection: {str(e)}")

    def connect_as_guest(self):
        """Connect as guest (client)"""
        if self.use_relay:
            self._start_relay(role="guest")
            return
        if self.is_host:
            self.error_occurred.emit("Cannot connect as guest when initialized as host")
            return

        def connect_task():
            self._connect_guest_with_retries(initial=True)

        threading.Thread(target=connect_task, daemon=True).start()

    def _connect_guest_once(self) -> bool:
        """Single guest connect attempt, returns True if success."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5.0)
        try:
            sock.connect((self.host_ip, self.port))
            sock.settimeout(None)
            self.socket = sock
            self.running = True
            self.connection_status_changed.emit(True, f"Connected to host at {self.host_ip}:{self.port}")
            self._start_io_threads(self.socket)
            return True
        except Exception as e:
            self.error_occurred.emit(f"Failed to connect: {str(e)}")
            self.connection_status_changed.emit(False, "Connection failed")
            try:
                sock.close()
            except Exception:
                pass
            return False

    def _connect_guest_with_retries(self, initial: bool = False):
        """Guest auto reconnect loop with exponential backoff."""
        delay = self._reconnect_delay_base
        first_attempt = True
        self._reconnect_active = True

        while self._reconnect_active and not self.running:
            if not first_attempt or not initial:
                self.connection_status_changed.emit(False, f"尝试重新连接 Host，中断后等待 {int(delay)} 秒...")
                time.sleep(delay)
                delay = min(delay * 2, self._reconnect_delay_max)

            first_attempt = False

            if self._connect_guest_once():
                self._reconnect_active = False
                break

    def _start_relay(self, role: str):
        self._relay_role = role

        def connect_task():
            self._connect_relay_with_retries(initial=True)

        threading.Thread(target=connect_task, daemon=True).start()

    def _connect_relay_once(self) -> bool:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5.0)
        try:
            print(f"[DEBUG] Connecting to relay {self.relay_host}:{self.relay_port} as {self._relay_role}")
            sock.connect((self.relay_host, self.relay_port))
            sock.settimeout(None)
            self.socket = sock
            self.running = True
            self.connection_status_changed.emit(True, f"Connected to relay at {self.relay_host}:{self.relay_port} as {self._relay_role}")
            self._start_io_threads(self.socket)
            self._send_packet({
                "type": "relay_register",
                "role": self._relay_role,
                "room_id": self.room_id,
                "timestamp": datetime.now().isoformat()
            })
            return True
        except Exception as e:
            self.error_occurred.emit(f"Failed to connect relay: {str(e)}")
            self.connection_status_changed.emit(False, "Relay connection failed")
            try:
                sock.close()
            except Exception:
                pass
            return False

    def _connect_relay_with_retries(self, initial: bool = False):
        delay = self._reconnect_delay_base
        first_attempt = True
        self._reconnect_active = True

        while self._reconnect_active and not self.running:
            if not first_attempt or not initial:
                self.connection_status_changed.emit(False, f"尝试重新连接中转服务器，等待 {int(delay)} 秒...")
                time.sleep(delay)
                delay = min(delay * 2, self._reconnect_delay_max)

            first_attempt = False

            if self._connect_relay_once():
                self._reconnect_active = False
                break

    def _start_io_threads(self, sock: socket.socket):
        """Start Receive and Heartbeat threads"""
        # Receive thread
        receive_thread = threading.Thread(target=self._receive_loop, args=(sock,), daemon=True)
        receive_thread.start()
        
        # Heartbeat thread
        self.last_heartbeat = time.time()
        self._heartbeat_thread = threading.Thread(target=self._heartbeat_loop, args=(sock,), daemon=True)
        self._heartbeat_thread.start()

    def send_message(self, sender: str, content: str) -> bool:
        """Send a standard text message"""
        return self._send_packet({
            "type": "message",
            "sender": sender,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })

    def send_ai_suggestion(self, suggestion: Dict) -> bool:
        """Broadcast AI suggestion to the peer"""
        return self._send_packet({
            "type": "ai_suggestion",
            "payload": suggestion
        })

    def send_ai_emotion(self, scores: Dict) -> bool:
        """Broadcast AI emotion scores to the peer"""
        return self._send_packet({
            "type": "ai_emotion",
            "scores": scores
        })

    def send_ai_memories(self, memories: list) -> bool:
        """Broadcast AI extracted memories to the peer"""
        return self._send_packet({
            "type": "ai_memories",
            "memories": memories
        })

    def send_ai_request(self) -> bool:
        """Send an explicit AI suggestion request to host"""
        return self._send_packet({
            "type": "ai_request",
            "timestamp": datetime.now().isoformat()
        })

    def send_typing(self, is_typing: bool) -> bool:
        return self._send_packet({
            "type": "typing",
            "is_typing": bool(is_typing),
            "timestamp": datetime.now().isoformat()
        })

    def _send_packet(self, data_dict: Dict) -> bool:
        """Low-level packet sending with thread safety"""
        if self.use_relay:
            target_socket = self.socket
        else:
            target_socket = self.client_socket if self.is_host else self.socket
        
        if not target_socket or not self.running:
            return False
            
        try:
            with QMutexLocker(self._mutex):
                data = json.dumps(data_dict).encode('utf-8')
                # 4-byte length prefix
                target_socket.sendall(len(data).to_bytes(4, 'big'))
                target_socket.sendall(data)
            return True
        except Exception as e:
            self.error_occurred.emit(f"Send error: {str(e)}")
            self._handle_disconnection()
            return False

    def _receive_loop(self, sock: socket.socket):
        """Main receiving loop"""
        while self.running:
            try:
                # Read length (blocking)
                length_data = self._recv_all(sock, 4)
                if not length_data:
                    break
                    
                length = int.from_bytes(length_data, 'big')
                
                # Read payload
                data = self._recv_all(sock, length)
                if not data:
                    break
                    
                message = json.loads(data.decode('utf-8'))
                self._process_message(message)
                
            except Exception as e:
                if self.running:
                    self.error_occurred.emit(f"Receive error: {str(e)}")
                break
        
        self._handle_disconnection()

    def _recv_all(self, sock: socket.socket, n: int) -> Optional[bytes]:
        """Helper to ensure exactly n bytes are read"""
        data = b''
        while len(data) < n:
            try:
                packet = sock.recv(n - len(data))
                if not packet:
                    return None
                data += packet
            except OSError:
                return None
        return data

    def _process_message(self, message: Dict):
        """Handle different message types"""
        msg_type = message.get("type", "message")
        
        if msg_type == "heartbeat":
            self.last_heartbeat = time.time()
            
        elif msg_type == "message":
            self.last_heartbeat = time.time()
            sender = message.get("sender", "Unknown")
            content = message.get("content", "")
            self.message_received.emit(sender, content)
        elif msg_type == "ai_suggestion":
            payload = message.get("payload", {})
            if isinstance(payload, dict):
                self.ai_suggestion_received.emit(payload)
        elif msg_type == "ai_emotion":
            scores = message.get("scores", {})
            if isinstance(scores, dict):
                self.ai_emotion_received.emit(scores)
        elif msg_type == "ai_memories":
            memories = message.get("memories", [])
            if isinstance(memories, list):
                self.ai_memories_received.emit(memories)
        elif msg_type == "ai_request":
            self.ai_request_received.emit()
        elif msg_type == "typing":
            is_typing = bool(message.get("is_typing", False))
            self.typing_status_changed.emit(is_typing)
        elif msg_type == "relay_register":
            pass

    def _heartbeat_loop(self, sock: socket.socket):
        """Send heartbeats and check for timeouts"""
        while self.running:
            # Send heartbeat
            success = self._send_packet({"type": "heartbeat"})
            if not success:
                break
                
            # Check timeout
            if time.time() - self.last_heartbeat > self.heartbeat_timeout:
                self.error_occurred.emit("Connection timed out")
                self._handle_disconnection()
                break
                
            time.sleep(self.heartbeat_interval)

    def _handle_disconnection(self):
        """Clean up resources on disconnect"""
        if not self.running:
            return

        self.running = False
        self.connection_status_changed.emit(False, "Disconnected")
        self.stop()

        if not self._reconnect_active:
            if self.use_relay:
                self._reconnect_thread = threading.Thread(target=self._connect_relay_with_retries, daemon=True)
                self._reconnect_thread.start()
            elif not self.is_host:
                self._reconnect_thread = threading.Thread(target=self._connect_guest_with_retries, daemon=True)
                self._reconnect_thread.start()

    def stop(self):
        """Stop network communication"""
        self.running = False
        self._reconnect_active = False
        try:
            if self.client_socket:
                self.client_socket.close()
            if self.socket:
                self.socket.close()
        except Exception:
            pass
