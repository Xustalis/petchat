#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""
PetChat Server - PyQt6 GUI Application
Routes messages and manages AI services.
"""


import sys
import socket
import threading
import json
import time
from typing import Dict, Optional, List, Any
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QObject, pyqtSignal, QThread, QRunnable, QThreadPool, pyqtSlot, QTimer

from ui.server_window import ServerMainWindow
from core.protocol import (
    Protocol, MessageType, HEADER_SIZE,
    AIAnalysisRequest, AISuggestion, AIEmotion, AIMemory,
    pack_message, unpack_header, verify_crc
)
from core.ai_session_manager import AISessionManager
from core.server_core import PetChatServer, ServerCallbacks

# Global thread pool
thread_pool = None

class WorkerSignals(QObject):
    """Signals for AI Worker"""
    result = pyqtSignal(object)
    error = pyqtSignal(str)

class AIWorker(QRunnable):
    """Worker for executing AI tasks in background"""
    
    def __init__(self, func, *args, **kwargs):
        super().__init__()
        self.func = func
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()
        
    @pyqtSlot()
    def run(self):
        try:
            result = self.func(*self.args, **self.kwargs)
            self.signals.result.emit(result)
        except Exception as e:
            self.signals.error.emit(str(e))

class PyQtServerCallbacks(ServerCallbacks):
    """Bridge between Core Server events and PyQt Signals"""
    def __init__(self, signals):
        self.signals = signals
        
    def on_log(self, message):
        self.signals.log_signal.emit(message)
    
    def on_stats_update(self, msg_count, ai_req_count):
        self.signals.stats_signal.emit(msg_count, ai_req_count)
    
    def on_client_connected(self, user_id, name, address):
        self.signals.client_connected.emit(user_id, name, address)
        
    def on_client_disconnected(self, user_id):
        self.signals.client_disconnected.emit(user_id)
        
    def on_ai_request(self, user_id, request):
        self.signals.ai_request_received.emit(user_id, request)
    
    def on_error(self, error):
        self.signals.log_signal.emit(f"ERROR: {error}")

class ServerThread(QThread):
    """
    Background thread for TCP Server.
    Wraps the platform-agnostic PetChatServer.
    """
    # Signals to communicate with Main Thread (GUI/Controller)
    log_signal = pyqtSignal(str)
    stats_signal = pyqtSignal(int, int) # msg_count, ai_req_count
    client_connected = pyqtSignal(str, str, tuple) # id, name, address
    client_disconnected = pyqtSignal(str)
    ai_request_received = pyqtSignal(str, dict) # client_id, request_dict
    
    def __init__(self, host="0.0.0.0", port=8888):
        super().__init__()
        self.callbacks = PyQtServerCallbacks(self)
        self.core_server = PetChatServer(host, port, self.callbacks)
        
    def run(self):
        """Main server loop"""
        # Start the core server
        self.core_server.start()
        
        # Keep this thread alive while server is running
        # The actual accept loop is in a daemon thread managed by core_server
        # We perform a simple wait loop here
        while self.core_server.running:
            self.msleep(100) # Sleep 100ms
        
        # If we exit loop, ensure server is stopped
        self.core_server.stop()

    def stop(self):
        self.core_server.stop()
        self.quit()
        self.wait()

    def send_to_client(self, user_id: str, message: dict):
        """Send message to specific client"""
        self.core_server.send_to_client(user_id, message)

    def disconnect_user(self, user_id: str):
        """Force disconnect a user"""
        self.core_server.disconnect_user(user_id)
    
    # Expose stats properties for Controller
    @property
    def msg_count(self):
        return self.core_server.msg_count
        
    @property
    def ai_req_count(self):
        return self.core_server.ai_req_count


class ServerController(QObject):
    """Main Application Controller"""
    
    def __init__(self, window):
        super().__init__()
        self.window = window
        self.server_thread: Optional[ServerThread] = None
        self.session_manager = AISessionManager()
        self.ai_service = None
        self.persist_token_usage = True
        
        self._init_connections()
        self._load_config()
        
    def _init_connections(self):
        self.window.start_server_requested.connect(self.start_server)
        self.window.stop_server_requested.connect(self.stop_server)
        self.window.api_config_changed.connect(self.update_ai_config)
        self.window.disconnect_user_requested.connect(self.disconnect_user)
        # self.window.refresh_stats_requested.connect(self.refresh_stats) # Removed from UI
        # self.window.test_ai_requested.connect(self.test_ai_connection) # Removed from UI
        self.window.closeEvent = self.on_close

        # Rate Calculation Timer
        self.stats_timer = QTimer()
        self.stats_timer.setInterval(1000)
        self.stats_timer.timeout.connect(self._calculate_rates)
        
        self.last_msg_count = 0
        self.last_ai_count = 0
        self.last_time = time.time()

    def _load_config(self):
        """Load config from server_config.json and populate UI"""
        import json
        config_path = "server_config.json"
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
        except FileNotFoundError:
            config = {"server_port": 8888, "ai_config": {}}
        except Exception as e:
            self.window.log_message(f"Failed to load config: {e}")
            config = {"server_port": 8888, "ai_config": {}}
        
        # Populate UI
        ai_cfg = config.get("ai_config", {})
        self.window.port_input.setText(str(config.get("server_port", 8888)))
        self.window.api_key_input.setText(ai_cfg.get("api_key", ""))
        self.window.api_base_input.setText(ai_cfg.get("base_url", ""))
        self.window.model_input.setText(ai_cfg.get("model", ""))
        
        # Initialize AI Service if config exists
        if ai_cfg.get("api_key") and ai_cfg.get("base_url"):
            self.update_ai_config(
                ai_cfg.get("api_key", ""),
                ai_cfg.get("base_url", ""),
                ai_cfg.get("model", "gpt-4o-mini")
            )
        else:
            self.window.log_message("AI Service not configured. Please set API Key.")

    def _save_config(self, key, base, model):
        """Save config to server_config.json"""
        import json
        config_path = "server_config.json"
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
        except:
            config = {}
        
        config["server_port"] = int(self.window.port_input.text() or 8888)
        config["ai_config"] = {
            "api_key": key,
            "base_url": base,
            "model": model
        }
        
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
        
        self.window.log_message("Config saved.")

    def start_server(self, port):
        if self.server_thread and self.server_thread.isRunning():
            return
            
        self.server_thread = ServerThread(port=port)
        self.server_thread.log_signal.connect(self.window.log_message)
        # self.server_thread.stats_signal.connect(self.window.update_stats) # Handled by timer now
        self.server_thread.client_connected.connect(self.window.add_client)
        self.server_thread.client_disconnected.connect(self.window.remove_client)
        self.server_thread.ai_request_received.connect(self.handle_ai_request)
        
        self.server_thread.start()
        self.stats_timer.start()
        self.window.update_server_status(True)

    def stop_server(self):
        if self.server_thread:
            self.server_thread.stop()
            self.server_thread.quit()
            self.server_thread.wait()
            self.server_thread = None
        self.stats_timer.stop()
        self.window.update_server_status(False)

    def update_ai_config(self, key, base, model):
        try:
            from core.ai_service import AIService
            # Use 60s timeout for production, 30s for testing
            self.ai_service = AIService(api_key=key, api_base=base, model=model, timeout=60.0)
            self.window.log_message(f"AI Service configured: {model}")
            # Persist config
            self._save_config(key, base, model)
        except Exception as e:
            self.window.log_message(f"Failed to configure AI Service: {e}")

    def refresh_stats(self):
        """Manually refresh stats"""
        if self.server_thread:
            # Force UI update with current thread stats
            self.window.update_stats(self.server_thread.msg_count, self.server_thread.ai_req_count)
        # Update token stats from session manager
        self.window.update_token_stats(self.session_manager.get_usage())

    def test_ai_connection(self, key, base, model):
        self.window.log_message(f"Testing connection to {base}...")
        worker = AIWorker(self._run_connection_test, key, base, model)
        # Use helper methods to update both log and UI label
        worker.signals.result.connect(self._on_test_success)
        worker.signals.error.connect(self._on_test_error)
        QThreadPool.globalInstance().start(worker)

    def _on_test_success(self, result):
        self.window.log_message(f"Connection Result:\n{result}")
        # Show concise success message in UI (e.g., first line)
        summary = result.split('\n')[0]
        self.window.show_ai_result(summary, True)

    def _on_test_error(self, error):
        self.window.log_message(f"Connection Failed: {error}")
        msg = str(error)
        # Translate common errors for better UX
        if "timed out" in msg.lower() or "timeout" in msg.lower():
            msg = "连接超时 (请检查Base URL或网络)"
        elif "connection refused" in msg.lower():
            msg = "连接被拒绝 (服务端未启动?)"
        self.window.show_ai_result(msg, False)

    def _run_connection_test(self, key, base, model):
        import requests
        
        # 1. Diagnostic: Check network reachability first
        self._check_network_reachability(base)
        
        base = base.rstrip('/')
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {key or 'lm-studio'}"}
        errors = []
        
        # Try listing models first
        try:
            resp = requests.get(f"{base}/models", headers=headers, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            model_names = [m["id"] for m in data.get("data", [])]
            if model in model_names:
                return f"✅ SUCCESS: Connected!\nModel '{model}' is available."
            else:
                return f"✅ CONNECTED (Warning): Model '{model}' not found.\nAvailable: {', '.join(model_names[:3])}..."
        except Exception as e:
            errors.append(f"List Models: {e}")

        # Try chat completion as ultimate test
        try:
            payload = {"model": model, "messages": [{"role": "user", "content": "hi"}], "max_tokens": 5}
            resp = requests.post(f"{base}/chat/completions", json=payload, headers=headers, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            return f"✅ SUCCESS: Chat completion worked!\nResponse: {content}"
        except Exception as e2:
            errors.append(f"Chat Completion: {e2}")
             
        # If both failed, raise comprehensive error
        raise Exception(f"Connection Failed.\n1. {errors[0]}\n2. {errors[1]}")


    def _check_network_reachability(self, url):
        """Attempt raw connection to base URL to diagnose network issues."""
        import urllib.request
        from urllib.parse import urlparse
        import socket
        
        try:
            parsed = urlparse(url)
            host = parsed.hostname
            port = parsed.port or (443 if parsed.scheme == 'https' else 80)
            
            # Simple TCP connect check
            sock = socket.create_connection((host, port), timeout=3)
            sock.close()
        except Exception as e:
            # If TCP fails, it's definitely network/firewall/IP
             raise Exception(f"Network Unreachable: Cannot connect to {host}:{port}.\nError: {e}\nCheck IP, Port, and Firewall.")

    def disconnect_user(self, user_id):
        if self.server_thread:
            self.server_thread.disconnect_user(user_id)

    def handle_ai_request(self, user_id, request_dict):
        """Process AI request in background"""
        if not self.ai_service:
            self.window.log_message("Request dropped: AI Service not ready")
            # Should send error response back to client?
            return

        conversation_id = request_dict.get("conversation_id")
        context_snapshot = request_dict.get("context_snapshot", [])
        
        # Update session context
        self.session_manager.update_context(conversation_id, context_snapshot)
        
        # Submit to thread pool
        worker = AIWorker(self._process_ai, conversation_id, context_snapshot)
        worker.signals.result.connect(lambda res: self._on_ai_result(user_id, res))
        worker.signals.error.connect(lambda err: self.window.log_message(f"AI Error: {err}"))
        
        QThreadPool.globalInstance().start(worker)

    def _process_ai(self, conversation_id, context_messages):
        # This runs in background thread
        # 1. Analyze emotion
        emotions = self.ai_service.analyze_emotion(context_messages)
        
        # 2. Extract memories
        memories = self.ai_service.extract_memories(context_messages)
        
        # 3. Generate suggestion
        suggestion = self.ai_service.generate_suggestion(context_messages)
        
        return {
            "conversation_id": conversation_id,
            "emotion": emotions,
            "memories": memories,
            "suggestion": suggestion
        }

    def _on_ai_result(self, user_id, result):
        # Runs in Main Thread
        cid = result["conversation_id"]
        
        # Send results back to client
        if self.server_thread:
            # Send Emotion
            if result["emotion"]:
                msg = AIEmotion(cid, result["emotion"]).to_dict()
                self.server_thread.send_to_client(user_id, msg)
                
            # Send Memories
            if result["memories"]:
                msg = AIMemory(cid, result["memories"]).to_dict()
                self.server_thread.send_to_client(user_id, msg)
                
            # Send Suggestion
            if result["suggestion"]:
                s = result["suggestion"]
                msg = AISuggestion(cid, s["title"], s["content"], s.get("type", "suggestion")).to_dict()
                self.server_thread.send_to_client(user_id, msg)
        
        # Update stats
        # self.session_manager.track_usage(cid, tokens) # Need token usage from AIService to track strictly
        self.window.update_token_stats(self.session_manager.get_usage())
        self.window.log_message(f"AI processed for {user_id} (Conv: {cid})")

    def _calculate_rates(self):
        if not self.server_thread: return
        
        current_time = time.time()
        dt = current_time - self.last_time
        if dt < 0.1: return
        
        msg_count = self.server_thread.msg_count
        ai_count = self.server_thread.ai_req_count
        
        msg_rate = (msg_count - self.last_msg_count) / dt
        ai_rate = (ai_count - self.last_ai_count) / dt * 60 # per minute
        
        self.last_msg_count = msg_count
        self.last_ai_count = ai_count
        self.last_time = current_time
        
        self.window.update_charts(msg_rate, ai_rate)
        self.window.update_stats(msg_count, ai_count)

    def on_close(self, event):
        self.stop_server()
        # Save token usage if needed
        import json
        try:
             with open("server_token_usage.json", "w") as f:
                 json.dump(self.session_manager.get_usage(), f)
        except:
            pass
        event.accept()

def main():
    app = QApplication(sys.argv)
    window = ServerMainWindow()
    controller = ServerController(window)
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
