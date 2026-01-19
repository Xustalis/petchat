import sys
import traceback
import os
import time
import logging
from datetime import datetime

class CrashReporter:
    """
    Handles unhandled exceptions and logs them to a file.
    """
    def __init__(self, log_dir="logs"):
        self.log_dir = log_dir
        self._setup_logging()
        
    def _setup_logging(self):
        if not os.path.exists(self.log_dir):
            try:
                os.makedirs(self.log_dir)
            except Exception as e:
                print(f"Failed to create log directory: {e}")
                
    def install(self):
        """Install the exception hook"""
        sys.excepthook = self._handle_exception
        print("[CrashReporter] Installed exception hook")

    def _handle_exception(self, exc_type, exc_value, exc_traceback):
        """Callback for sys.excepthook"""
        # Ignore KeyboardInterrupt so Ctrl+C still works
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"client_crash_{timestamp}.log"
        filepath = os.path.join(self.log_dir, filename)
        
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(f"PetChat Client Crash Report\n")
                f.write(f"Time: {datetime.now().isoformat()}\n")
                f.write(f"OS: {sys.platform}\n")
                f.write(f"Python: {sys.version}\n")
                f.write("-" * 50 + "\n")
                f.write("Exception:\n")
                traceback.print_exception(exc_type, exc_value, exc_traceback, file=f)
                f.write("-" * 50 + "\n")
                
            print(f"\n[CRASH] Application crashed! traceback saved to: {filepath}")
            # Also print to stderr for immediate feedback
            traceback.print_exception(exc_type, exc_value, exc_traceback)
            
        except Exception as e:
            print(f"[CRASH] Failed to write crash log: {e}")
            traceback.print_exception(exc_type, exc_value, exc_traceback)

        # Optional: Show a GUI dialog if PyQt is running?
        # For now, we just exit with error code
        sys.exit(1)
