import socket
import threading
import json
import time
import logging
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Dict, Tuple


class RelayServer:
    def __init__(self, host: str = "0.0.0.0", port: int = 9000):
        self.host = host
        self.port = port
        self.rooms: Dict[str, Dict[str, socket.socket]] = {}
        self.clients: Dict[socket.socket, Dict] = {}
        self.lock = threading.Lock()
        self.logger = logging.getLogger("relay_server")
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
        self.logger.setLevel(logging.INFO)
        if not self.logger.handlers:
            self.logger.addHandler(handler)
        self.heartbeat_timeout = 60.0

    def start(self):
        server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_sock.bind((self.host, self.port))
        server_sock.listen(100)
        self.logger.info(f"Relay server listening on {self.host}:{self.port}")

        threading.Thread(target=self._monitor_loop, daemon=True).start()
        threading.Thread(target=self._start_status_server, daemon=True).start()

        try:
            while True:
                conn, addr = server_sock.accept()
                self.logger.info(f"Incoming TCP connection from {addr[0]}:{addr[1]}")
                threading.Thread(target=self._handle_client, args=(conn, addr), daemon=True).start()
        finally:
            server_sock.close()

    def _handle_client(self, conn: socket.socket, addr: Tuple[str, int]):
        room_id = None
        role = None
        try:
            while True:
                length_data = self._recv_all(conn, 4)
                if not length_data:
                    break
                length = int.from_bytes(length_data, "big")
                payload = self._recv_all(conn, length)
                if not payload:
                    break

                try:
                    message = json.loads(payload.decode("utf-8"))
                except Exception as e:
                    self._send_error(conn, "INVALID_JSON", f"Invalid JSON payload: {e}")
                    break

                msg_type = message.get("type")
                now = time.time()

                if msg_type == "relay_register":
                    room_id = str(message.get("room_id") or "default")
                    role = str(message.get("role") or "guest")
                    if role not in ("host", "guest"):
                        self._send_error(conn, "INVALID_ROLE", f"Invalid role: {role}")
                        break
                    if not room_id:
                        self._send_error(conn, "INVALID_ROOM", "Empty room_id")
                        break
                    ok, reason = self._register_client(room_id, role, conn, addr, now)
                    if not ok:
                        self._send_error(conn, "REGISTER_FAILED", reason)
                        break
                    self._send_ack(conn, room_id, role)
                    continue

                self._update_last_seen(conn, now)

                if msg_type == "heartbeat":
                    self.logger.debug(f"Heartbeat from {addr[0]}:{addr[1]} room={room_id} role={role}")
                    raw = length_data + payload
                    target = self._get_target(room_id, role)
                    if target:
                        try:
                            target.sendall(raw)
                        except OSError:
                            pass
                    continue

                raw = length_data + payload
                target = self._get_target(room_id, role)
                if target:
                    try:
                        target.sendall(raw)
                    except OSError as e:
                        self.logger.warning(f"Forward error: {e}")
        finally:
            self._cleanup_connection(conn, room_id, role, addr)

    def _register_client(self, room_id: str, role: str, conn: socket.socket, addr: Tuple[str, int], now: float):
        with self.lock:
            room = self.rooms.get(room_id)
            if not room:
                room = {}
                self.rooms[room_id] = room
            existing = room.get(role)
            if existing and existing is not conn:
                return False, f"Role {role} already connected in room {room_id}"
            room[role] = conn
            self.clients[conn] = {
                "room_id": room_id,
                "role": role,
                "addr": f"{addr[0]}:{addr[1]}",
                "last_seen": now,
            }
            self.logger.info(f"Client {addr[0]}:{addr[1]} registered as {role} in room {room_id}, active={len(self.clients)}")
            return True, ""

    def _update_last_seen(self, conn: socket.socket, now: float):
        with self.lock:
            meta = self.clients.get(conn)
            if meta:
                meta["last_seen"] = now

    def _cleanup_connection(self, conn: socket.socket, room_id: str | None, role: str | None, addr: Tuple[str, int]):
        with self.lock:
            if conn in self.clients:
                meta = self.clients.pop(conn)
                rid = meta.get("room_id")
                rrole = meta.get("role")
                room = self.rooms.get(rid)
                if room and room.get(rrole) is conn:
                    room.pop(rrole, None)
                    if not room:
                        self.rooms.pop(rid, None)
                self.logger.info(f"Client {meta.get('addr')} disconnected from room {rid} role {rrole}, active={len(self.clients)}")
            elif room_id and role:
                room = self.rooms.get(room_id)
                if room and room.get(role) is conn:
                    room.pop(role, None)
                    if not room:
                        self.rooms.pop(room_id, None)
        try:
            conn.close()
        except OSError:
            pass

    def _send_ack(self, conn: socket.socket, room_id: str, role: str):
        with self.lock:
            room = self.rooms.get(room_id) or {}
            active_in_room = len(room)
            active_total = len(self.clients)
        payload = {
            "type": "relay_ack",
            "room_id": room_id,
            "role": role,
            "active_in_room": active_in_room,
            "active_total": active_total,
        }
        self._send_raw(conn, payload)

    def _send_error(self, conn: socket.socket, code: str, message: str):
        self.logger.warning(f"Send error to client: {code} {message}")
        payload = {
            "type": "relay_error",
            "code": code,
            "message": message,
        }
        self._send_raw(conn, payload)

    def _send_raw(self, conn: socket.socket, payload: Dict):
        try:
            data = json.dumps(payload).encode("utf-8")
            conn.sendall(len(data).to_bytes(4, "big"))
            conn.sendall(data)
        except OSError as e:
            self.logger.warning(f"Failed to send payload to client: {e}")

    def _get_target(self, room_id: str | None, role: str | None) -> socket.socket | None:
        if not room_id or not role:
            return None
        other_role = "guest" if role == "host" else "host"
        with self.lock:
            room = self.rooms.get(room_id)
            if not room:
                return None
            return room.get(other_role)

    def _recv_all(self, conn: socket.socket, n: int) -> bytes | None:
        data = b""
        while len(data) < n:
            try:
                part = conn.recv(n - len(data))
                if not part:
                    return None
                data += part
            except OSError:
                return None
        return data

    def _monitor_loop(self):
        while True:
            time.sleep(10.0)
            now = time.time()
            stale = []
            with self.lock:
                for conn, meta in list(self.clients.items()):
                    last_seen = meta.get("last_seen", 0)
                    if now - last_seen > self.heartbeat_timeout:
                        stale.append((conn, meta))
            for conn, meta in stale:
                self.logger.warning(f"Heartbeat timeout for {meta.get('addr')} room={meta.get('room_id')} role={meta.get('role')}")
                self._cleanup_connection(conn, meta.get("room_id"), meta.get("role"), ("", 0))

    def _start_status_server(self):
        server = self

        class StatusHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                if self.path != "/status":
                    self.send_response(404)
                    self.end_headers()
                    return
                with server.lock:
                    rooms = {
                        rid: {r: server.clients.get(conn, {}).get("addr", "") for r, conn in room.items()}
                        for rid, room in server.rooms.items()
                    }
                    data = {
                        "host": server.host,
                        "port": server.port,
                        "active_connections": len(server.clients),
                        "rooms": rooms,
                    }
                body = json.dumps(data).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, format, *args):
                return

        try:
            httpd = HTTPServer((self.host, self.port + 1), StatusHandler)
            self.logger.info(f"Status server listening on {self.host}:{self.port + 1}")
            httpd.serve_forever()
        except OSError as e:
            self.logger.warning(f"Failed to start status server: {e}")


if __name__ == "__main__":
    server = RelayServer()
    server.start()
