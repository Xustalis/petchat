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
        return self.config.get('api_key')
    
    def get_api_base(self) -> Optional[str]:
        return self.config.get('api_base')
    
    def set_api_key(self, api_key: str):
        self.config['api_key'] = api_key
        self._save_config()
    
    def set_api_base(self, api_base: str):
        if api_base:
            self.config['api_base'] = api_base
        else:
            self.config.pop('api_base', None)
        self._save_config()
    
    def set_api_config(self, api_key: str, api_base: str = ""):
        self.set_api_key(api_key)
        self.set_api_base(api_base)
    
    def has_api_config(self) -> bool:
        return bool(self.config.get('api_key'))

    def get_user_name(self) -> Optional[str]:
        return self.config.get('user_name')

    def get_user_avatar(self) -> Optional[str]:
        return self.config.get('user_avatar')
    
    def get_user_id(self) -> Optional[str]:
        """Get stored user ID (UUID)"""
        return self.config.get('user_id')
    
    def set_user_id(self, user_id: str):
        """Set user ID (UUID) - should only be called once on first run"""
        self.config['user_id'] = user_id
        self._save_config()

    def set_user_profile(self, name: str, avatar: str = "", user_id: str = ""):
        self.config['user_name'] = name
        if avatar:
            self.config['user_avatar'] = avatar
        else:
            self.config.pop('user_avatar', None)
        if user_id:
            self.config['user_id'] = user_id
        self._save_config()

    def reset(self):
        """Reset configuration to defaults"""
        self.config = {}
        try:
            if self.config_file.exists():
                self.config_file.unlink()
        except Exception as e:
            print(f"Error resetting config: {e}")

