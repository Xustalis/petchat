"""
PetChat Server Core - Platform Agnostic
Handles TCP networking, client management, and message routing.
No GUI dependencies (PyQt6 free).
"""
import socket
import threading
import json
import time
import logging
from typing import Dict, Optional, List, Any, Callable

from core.protocol import (
    MessageType, HEADER_SIZE,
    pack_message, unpack_header, verify_crc
)

class ServerCallbacks:
    """Interface for server callbacks"""
    def on_log(self, message: str): pass
    def on_stats_update(self, msg_count: int, ai_req_count: int): pass
    def on_client_connected(self, user_id: str, name: str, address: tuple): pass
    def on_client_disconnected(self, user_id: str): pass
    def on_ai_request(self, user_id: str, request: dict): pass
    def on_error(self, error: str): pass

class PetChatServer:
    """
    Core Server Logic.
    Manages socket connections and protocol handling.
    """
    
    def __init__(self, host: str = "0.0.0.0", port: int = 8888, callbacks: ServerCallbacks = None):
        self.host = host
        self.port = port
        self.callbacks = callbacks or ServerCallbacks()
        
        self.running = False
        self.server_socket: Optional[socket.socket] = None
        
        self.clients: Dict[str, Dict] = {}
        self.clients_lock = threading.Lock()
        
        self.msg_count = 0
        self.ai_req_count = 0
        
        # Daemon thread for accepting connections
        self.accept_thread: Optional[threading.Thread] = None

    def start(self):
        """Start the server"""
        if self.running:
            return

        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(10)
            
            self.running = True
            self._log(f"Server started on {self.host}:{self.port}")
            
            self.accept_thread = threading.Thread(target=self._accept_loop, daemon=True)
            self.accept_thread.start()
            
        except Exception as e:
            self._error(f"Failed to start server: {e}")
            self.stop()

    def stop(self):
        """Stop the server"""
        self.running = False
        
        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass
            self.server_socket = None
            
        # Close all client sockets
        with self.clients_lock:
            for client in self.clients.values():
                try:
                    client["socket"].close()
                except:
                    pass
            self.clients.clear()
            
        self._log("Server stopped")

    def _accept_loop(self):
        """Main loop for accepting new connections"""
        while self.running and self.server_socket:
            try:
                # Blocking accept
                client_sock, addr = self.server_socket.accept()
                
                # Spawn handling thread
                t = threading.Thread(
                    target=self._handle_client_connection,
                    args=(client_sock, addr),
                    daemon=True
                )
                t.start()
                
            except OSError:
                # Socket closed
                break
            except Exception as e:
                self._error(f"Accept error: {e}")

    def send_to_client(self, user_id: str, message: dict):
        """Send message to specific client"""
        with self.clients_lock:
            client = self.clients.get(user_id)
            if client:
                self._send_raw(client["socket"], message)

    def disconnect_user(self, user_id: str):
        """Force disconnect a user"""
        with self.clients_lock:
            client = self.clients.get(user_id)
            if client:
                try:
                    client["socket"].close()
                except:
                    pass
                # Cleanup will happen in _handle_client_connection loop

    # --- Internal methods ---

    def _log(self, msg: str):
        if self.callbacks:
            self.callbacks.on_log(msg)

    def _error(self, msg: str):
        if self.callbacks:
            self.callbacks.on_error(msg)
            self.callbacks.on_log(f"ERROR: {msg}")

    def _handle_client_connection(self, sock: socket.socket, addr):
        user_id = None
        try:
            while self.running:
                header = self._recv_exact(sock, HEADER_SIZE)
                if not header: break
                
                length, expected_crc = unpack_header(header)
                payload = self._recv_exact(sock, length)
                if not payload: break
                
                if not verify_crc(payload, expected_crc):
                    continue
                
                try:
                    message = json.loads(payload.decode('utf-8'))
                except:
                    continue
                    
                msg_type = message.get("type")
                
                # Handle Register
                if msg_type == MessageType.REGISTER.value:
                    user_id = self._handle_register(sock, message, addr)
                
                # Handle Chat
                elif msg_type == MessageType.CHAT_MESSAGE.value:
                    self._handle_chat(message)
                    self.msg_count += 1
                    if self.callbacks:
                        self.callbacks.on_stats_update(self.msg_count, self.ai_req_count)
                
                # Handle AI Request
                elif msg_type == MessageType.AI_ANALYSIS_REQUEST.value:
                    if user_id:
                        self.ai_req_count += 1
                        if self.callbacks:
                            self.callbacks.on_stats_update(self.msg_count, self.ai_req_count)
                            self.callbacks.on_ai_request(user_id, message)
                
                # Handle Heartbeat
                elif msg_type == MessageType.PING.value:
                    self._send_raw(sock, {"type": MessageType.PONG.value})

                # Handle other
                elif msg_type == MessageType.TYPING_STATUS.value:
                    self._broadcast(message, exclude=user_id)
                    
        except Exception as e:
            self._error(f"Error handling client {addr}: {e}")
        finally:
            if user_id:
                self._handle_disconnect(user_id)
            try:
                sock.close()
            except:
                pass

    def _recv_exact(self, sock, n):
        data = b''
        while len(data) < n:
            try:
                chunk = sock.recv(n - len(data))
                if not chunk: return None
                data += chunk
            except:
                return None
        return data

    def _send_raw(self, sock, message):
        try:
            packet = pack_message(message)
            sock.sendall(packet)
        except:
            pass

    def _handle_register(self, sock, message, addr):
        user_id = message.get("user_id")
        name = message.get("user_name", "Unknown")
        avatar = message.get("avatar", "")
        
        with self.clients_lock:
            self.clients[user_id] = {
                "socket": sock,
                "name": name,
                "avatar": avatar,
                "addr": addr
            }
        
        self._log(f"User registered: {name} ({user_id})")
        if self.callbacks:
            self.callbacks.on_client_connected(user_id, name, addr)
        
        # Notify others
        self._broadcast({
            "type": MessageType.USER_JOINED.value,
            "user_id": user_id,
            "user_name": name,
            "avatar": avatar
        }, exclude=user_id)
        
        # Send online users
        users = []
        with self.clients_lock:
            for uid, info in self.clients.items():
                if uid != user_id:
                    users.append({
                        "user_id": uid,
                        "user_name": info["name"],
                        "avatar": info["avatar"]
                    })
        self._send_raw(sock, {"type": MessageType.ONLINE_USERS.value, "users": users})
        return user_id

    def _handle_disconnect(self, user_id):
        with self.clients_lock:
            if user_id in self.clients:
                del self.clients[user_id]
        
        self._log(f"User disconnected: {user_id}")
        if self.callbacks:
            self.callbacks.on_client_disconnected(user_id)
        
        self._broadcast({
            "type": MessageType.USER_LEFT.value,
            "user_id": user_id
        })

    def _handle_chat(self, message):
        target = message.get("target", "public")
        sender = message.get("sender_id")
        
        if target == "public":
            self._broadcast(message, exclude=sender)
        else:
            with self.clients_lock:
                client = self.clients.get(target)
                if client:
                    self._send_raw(client["socket"], message)

    def _broadcast(self, message, exclude=None):
        with self.clients_lock:
            for uid, client in self.clients.items():
                if uid == exclude: continue
                self._send_raw(client["socket"], message)

    def broadcast_message(self, message: dict):
        """Public API to broadcast message"""
        self._broadcast(message)

