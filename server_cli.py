import argparse
import sys
import json
import logging
import signal
import time
from pathlib import Path
from core.server_core import PetChatServer, ServerCallbacks

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("server.log", encoding='utf-8')
    ]
)
logger = logging.getLogger("PetChatCLI")

class CLICallbacks(ServerCallbacks):
    """Callbacks for CLI interaction"""
    def on_log(self, message: str):
        logger.info(message)
        
    def on_error(self, error: str):
        logger.error(error)
        
    def on_stats_update(self, msg_count: int, ai_req_count: int):
        # We don't want to spam stdout with every update
        pass
        
    def on_client_connected(self, user_id, name, address):
        logger.info(f"Client Connected: {name} ({user_id}) from {address}")
        
    def on_client_disconnected(self, user_id):
        logger.info(f"Client Disconnected: {user_id}")
        
    def on_ai_request(self, user_id, request):
        logger.info(f"AI Request from {user_id}")

def load_config(path="server_config.json"):
    if Path(path).exists():
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"server_port": 8888, "ai_config": {}}

def save_config(config, path="server_config.json"):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=4, ensure_ascii=False)
    print(f"Configuration saved to {path}")

def cmd_start(args):
    """Start the server"""
    config = load_config()
    # CLI args override config file
    port = args.port or config.get("server_port", 8888)
    
    print(f"Starting PetChat Server on port {port}...")
    
    server = PetChatServer(port=port, callbacks=CLICallbacks())
    
    # helper for graceful shutdown
    def signal_handler(sig, frame):
        print("\nStopping server...")
        server.stop()
        sys.exit(0)
        
    signal.signal(signal.SIGINT, signal_handler)
    if hasattr(signal, 'SIGTERM'):
        signal.signal(signal.SIGTERM, signal_handler)
    
    server.start()
    
    # Keep main thread alive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        server.stop()

def cmd_config(args):
    """Manage configuration"""
    config = load_config()
    
    if args.action == "show":
        print(json.dumps(config, indent=4, ensure_ascii=False))
        
    elif args.action == "set":
        if not args.key or not args.value:
            print("Error: --key and --value required for set action")
            return
            
        # Handle neseted keys (e.g. ai_config.api_key)
        keys = args.key.split('.')
        target = config
        for k in keys[:-1]:
            target = target.setdefault(k, {})
        target[keys[-1]] = args.value
        
        save_config(config)
        
    elif args.action == "get":
        if not args.key:
            print("Error: --key required for get action")
            return
            
        keys = args.key.split('.')
        val = config
        try:
            for k in keys:
                val = val[k]
            print(val)
        except:
            print(f"Key '{args.key}' not found")

def cmd_logs(args):
    """View server logs"""
    log_file = Path("server.log")
    if not log_file.exists():
        print("No log file found.")
        return
        
    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
        # Show last N lines
        n = min(len(lines), args.lines)
        for line in lines[-n:]:
            print(line.strip())
            
        if args.follow:
            with open(log_file, 'r', encoding='utf-8') as f:
                f.seek(0, 2) # Go to end
                while True:
                    line = f.readline()
                    if line:
                        print(line.strip())
                    else:
                        time.sleep(0.1)
    except KeyboardInterrupt:
        print("\nStopped.")


def init_parser():
    parser = argparse.ArgumentParser(description="PetChat Server CLI")
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # Start Command
    start_parser = subparsers.add_parser("start", help="Start the server")
    start_parser.add_argument("--port", type=int, help="Server port (overrides config)")
    
    # Config Command
    config_parser = subparsers.add_parser("config", help="Manage configuration")
    config_parser.add_argument("action", choices=["show", "set", "get"], help="Action to perform")
    config_parser.add_argument("--key", help="Config key (e.g. server_port or ai_config.api_key)")
    config_parser.add_argument("--value", help="Config value")

    # Logs Command
    logs_parser = subparsers.add_parser("logs", help="View server logs")
    logs_parser.add_argument("--lines", "-n", type=int, default=20, help="Number of lines")
    logs_parser.add_argument("--follow", "-f", action="store_true", help="Follow log output")

    return parser

if __name__ == "__main__":
    parser = init_parser()
    args = parser.parse_args()
    
    if args.command == "start":
        cmd_start(args)
    elif args.command == "config":
        cmd_config(args)
    elif args.command == "logs":
        cmd_logs(args)
    else:
        parser.print_help()
