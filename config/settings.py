"""Settings and configuration management"""
import os
from typing import Optional


class Settings:
    """Application settings"""
    
    # Default values
    DEFAULT_PORT = 8888
    DEFAULT_RELAY_PORT = 9000
    DEFAULT_HOST_IP = "0.0.0.0"  # Bind to all interfaces for host
    DEFAULT_GUEST_IP = "127.0.0.1"
    
    # Emotion analysis settings
    EMOTION_ANALYSIS_INTERVAL = 5  # Analyze emotion every N messages
    RECENT_MESSAGES_FOR_EMOTION = 5  # Number of recent messages to analyze
    
    # Memory extraction settings
    MEMORY_EXTRACTION_INTERVAL = 10  # Extract memories every N messages
    
    # Suggestion settings
    SUGGESTION_CHECK_INTERVAL = 3  # Check for suggestions every N messages
    
    @staticmethod
    def get_api_key() -> Optional[str]:
        """Get OpenAI API key from environment"""
        return os.getenv("OPENAI_API_KEY")
    
    @staticmethod
    def get_api_base() -> Optional[str]:
        """Get OpenAI API base URL from environment"""
        return os.getenv("OPENAI_API_BASE")

