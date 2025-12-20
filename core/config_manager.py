"""Configuration manager for storing API keys and settings"""
import json
import os
from typing import Optional
from pathlib import Path


class ConfigManager:
    """Manages application configuration"""
    
    def __init__(self, config_file: str = "config.json"):
        """
        Initialize config manager
        
        Args:
            config_file: Path to config file
        """
        self.config_file = Path(config_file)
        self.config = self._load_config()
    
    def _load_config(self) -> dict:
        """Load configuration from file"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading config: {e}")
                return {}
        return {}
    
    def _save_config(self):
        """Save configuration to file"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving config: {e}")
    
    def get_api_key(self) -> Optional[str]:
        """Get API key"""
        return self.config.get('api_key')
    
    def get_api_base(self) -> Optional[str]:
        """Get API base URL"""
        return self.config.get('api_base')
    
    def set_api_key(self, api_key: str):
        """Set API key"""
        self.config['api_key'] = api_key
        self._save_config()
    
    def set_api_base(self, api_base: str):
        """Set API base URL"""
        if api_base:
            self.config['api_base'] = api_base
        else:
            self.config.pop('api_base', None)
        self._save_config()
    
    def set_api_config(self, api_key: str, api_base: str = ""):
        """Set both API key and base"""
        self.set_api_key(api_key)
        self.set_api_base(api_base)
    
    def has_api_config(self) -> bool:
        """Check if API config exists"""
        return bool(self.config.get('api_key'))

    def reset(self):
        """Reset configuration to defaults"""
        self.config = {}
        try:
            if self.config_file.exists():
                self.config_file.unlink()
        except Exception as e:
            print(f"Error resetting config: {e}")

