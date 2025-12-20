"""
Window Manager for handling multi-window application state and thread pool.
Provides simple tracking without using PyQt6 singleton pattern.
"""
from typing import Dict, Optional
import uuid

class WindowManager:
    """Manages application windows and thread pool"""
    
    def __init__(self):
        """Initialize window manager"""
        self._windows: Dict[str, object] = {}
    
    def register_window(self, window: object) -> str:
        """Register a new window instance and return its ID"""
        window_id = str(uuid.uuid4())
        self._windows[window_id] = window
        return window_id
        
    def unregister_window(self, window_id: str):
        """Unregister a window instance"""
        if window_id in self._windows:
            del self._windows[window_id]
            
    def get_window(self, window_id: str) -> Optional[object]:
        """Get window by ID"""
        return self._windows.get(window_id)
        
    def get_all_windows(self) -> list[object]:
        """Get all registered windows"""
        return list(self._windows.values())

# Simple singleton implementation
class WindowManagerSingleton:
    _instance = None
    
    @staticmethod
    def get_instance():
        """Get the global window manager instance"""
        if WindowManagerSingleton._instance is None:
            WindowManagerSingleton._instance = WindowManager()
        return WindowManagerSingleton._instance

# Global accessor
window_manager = WindowManagerSingleton.get_instance
