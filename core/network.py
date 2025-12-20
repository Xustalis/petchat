"""P2P network communication module with thread-safe signals"""
import socket
import threading
import json
import time
from typing import Optional, Dict
from datetime import datetime
from PyQt6.QtCore import QObject, pyqtSignal, QMutex, QMutexLocker

class NetworkManager(QObject):
    """
    Manages P2P communication between Host and Guest.
    Thread-safe implementation using PyQt signals.
    """
    
    # Signals for UI updates (must be emitted from QObject)
    message_received = pyqtSignal(str, str)  # sender, content
    connection_status_changed = pyqtSignal(bool, str)  # connected, message
    error_occurred = pyqtSignal(str)
    
    def __init__(self, is_host: bool = False, host_ip: str = "127.0.0.1", port: int = 8888):
        super().__init__()
        self.is_host = is_host
        self.host_ip = host_ip
        self.port = port
        
        self.socket: Optional[socket.socket] = None
        self.client_socket: Optional[socket.socket] = None
        
        self.running = False
        self._mutex = QMutex()
        
        # Heartbeat settings
        self.last_heartbeat = 0
        self.heartbeat_interval = 5.0
        self.heartbeat_timeout = 15.0
        self._heartbeat_thread: Optional[threading.Thread] = None

    def start_host(self):
        """Start as host (server)"""
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
        if self.is_host:
            self.error_occurred.emit("Cannot connect as guest when initialized as host")
            return
        
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.settimeout(5.0)  # Connect timeout
        
        def connect_task():
            try:
                self.socket.connect((self.host_ip, self.port))
                self.socket.settimeout(None)  # Remove timeout for blocking recv
                self.running = True
                
                self.connection_status_changed.emit(True, f"Connected to host at {self.host_ip}:{self.port}")
                self._start_io_threads(self.socket)
                
            except Exception as e:
                self.error_occurred.emit(f"Failed to connect: {str(e)}")
                self.connection_status_changed.emit(False, "Connection failed")
        
        # Connect in a thread to avoid freezing UI
        threading.Thread(target=connect_task, daemon=True).start()

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

    def _send_packet(self, data_dict: Dict) -> bool:
        """Low-level packet sending with thread safety"""
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

    def stop(self):
        """Stop network communication"""
        self.running = False
        try:
            if self.client_socket:
                self.client_socket.close()
            if self.socket:
                self.socket.close()
        except Exception:
            pass
