"""
PetChat Server - Clean Client-Server Architecture
Simple TCP server that routes messages between connected clients.
"""
import socket
import threading
import json
import struct
import zlib
from typing import Dict, Optional

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


class PetChatServer:
    """Simple chat server that routes messages between clients"""
    
    def __init__(self, host: str = "0.0.0.0", port: int = 8888):
        self.host = host
        self.port = port
        self.running = False
        self.server_socket: Optional[socket.socket] = None
        
        # Connected clients: {user_id: {"socket": socket, "name": name, "avatar": avatar}}
        self.clients: Dict[str, Dict] = {}
        self.clients_lock = threading.Lock()
        
    def start(self):
        """Start the server"""
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(10)
        self.running = True
        
        print(f"[SERVER] PetChat Server started on {self.host}:{self.port}")
        print("[SERVER] Waiting for connections...")
        
        try:
            while self.running:
                try:
                    client_sock, addr = self.server_socket.accept()
                    print(f"[SERVER] New connection from {addr}")
                    threading.Thread(
                        target=self._handle_client, 
                        args=(client_sock, addr), 
                        daemon=True
                    ).start()
                except OSError:
                    break
        except KeyboardInterrupt:
            print("\n[SERVER] Shutting down...")
        finally:
            self.stop()
            
    def stop(self):
        """Stop the server"""
        self.running = False
        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass
        print("[SERVER] Server stopped")

    def _handle_client(self, sock: socket.socket, addr):
        """Handle a single client connection"""
        user_id = None
        
        try:
            while self.running:
                # Read header
                header = self._recv_exact(sock, HEADER_SIZE)
                if not header:
                    break
                    
                length, expected_crc = unpack_header(header)
                
                # Read payload
                payload = self._recv_exact(sock, length)
                if not payload:
                    break
                    
                # Verify CRC
                if not verify_crc(payload, expected_crc):
                    print(f"[SERVER] CRC error from {addr}")
                    continue
                
                # Parse message
                try:
                    message = json.loads(payload.decode('utf-8'))
                except json.JSONDecodeError:
                    print(f"[SERVER] Invalid JSON from {addr}")
                    continue
                
                msg_type = message.get("type")
                print(f"[SERVER] Received {msg_type} from {addr}")
                
                # Handle message types
                if msg_type == "register":
                    user_id = self._handle_register(sock, message)
                elif msg_type == "chat_message":
                    self._handle_chat_message(message)
                elif msg_type == "typing_status":
                    self._broadcast(message, exclude=message.get("sender_id"))
                    
        except Exception as e:
            print(f"[SERVER] Error handling client {addr}: {e}")
        finally:
            self._handle_disconnect(user_id)
            try:
                sock.close()
            except:
                pass
            print(f"[SERVER] Connection closed: {addr}")

    def _recv_exact(self, sock: socket.socket, n: int) -> Optional[bytes]:
        """Receive exactly n bytes"""
        data = b''
        while len(data) < n:
            try:
                chunk = sock.recv(n - len(data))
                if not chunk:
                    return None
                data += chunk
            except:
                return None
        return data
        
    def _send_message(self, sock: socket.socket, message: dict) -> bool:
        """Send a message to a socket"""
        try:
            packet = pack_message(message)
            sock.sendall(packet)
            return True
        except Exception as e:
            print(f"[SERVER] Send error: {e}")
            return False

    def _handle_register(self, sock: socket.socket, message: dict) -> Optional[str]:
        """Register a new user"""
        user_id = message.get("user_id")
        user_name = message.get("user_name", "Unknown")
        avatar = message.get("avatar", "")
        
        if not user_id:
            return None
            
        with self.clients_lock:
            self.clients[user_id] = {
                "socket": sock,
                "name": user_name,
                "avatar": avatar
            }
        
        print(f"[SERVER] User registered: {user_name} ({user_id})")
        
        # Notify all other clients about new user
        self._broadcast({
            "type": "user_joined",
            "user_id": user_id,
            "user_name": user_name,
            "avatar": avatar
        }, exclude=user_id)
        
        # Send online users list to the new user
        self._send_online_users(sock, user_id)
        
        return user_id

    def _handle_chat_message(self, message: dict):
        """Route a chat message"""
        sender_id = message.get("sender_id")
        target = message.get("target", "public")
        
        print(f"[SERVER] Chat message from {message.get('sender_name')} -> {target}")
        
        if target == "public":
            # Broadcast to all except sender
            self._broadcast(message, exclude=sender_id)
        else:
            # Private message to specific user
            with self.clients_lock:
                target_client = self.clients.get(target)
                if target_client:
                    self._send_message(target_client["socket"], message)
                    print(f"[SERVER] Delivered private message to {target}")
                else:
                    print(f"[SERVER] Target user {target} not found")

    def _handle_disconnect(self, user_id: Optional[str]):
        """Handle user disconnection"""
        if not user_id:
            return
            
        with self.clients_lock:
            if user_id in self.clients:
                del self.clients[user_id]
        
        print(f"[SERVER] User disconnected: {user_id}")
        
        # Notify others
        self._broadcast({
            "type": "user_left",
            "user_id": user_id
        })

    def _broadcast(self, message: dict, exclude: str = None):
        """Send message to all connected clients"""
        with self.clients_lock:
            for uid, client in list(self.clients.items()):
                if exclude and uid == exclude:
                    continue
                self._send_message(client["socket"], message)

    def _send_online_users(self, sock: socket.socket, new_user_id: str):
        """Send list of online users to a client"""
        users = []
        with self.clients_lock:
            for uid, info in self.clients.items():
                if uid != new_user_id:  # Don't include self
                    users.append({
                        "user_id": uid,
                        "user_name": info["name"],
                        "avatar": info["avatar"]
                    })
        
        self._send_message(sock, {
            "type": "online_users",
            "users": users
        })


if __name__ == "__main__":
    server = PetChatServer()
    server.start()
