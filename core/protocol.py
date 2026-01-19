"""
Shared Protocol Module for PetChat
Defines message types, pack/unpack functions, and protocol constants.
Used by both server and client for consistent communication.
"""
import json
import struct
import zlib
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from enum import Enum


# Protocol constants
HEADER_SIZE = 8  # 4 bytes length + 4 bytes CRC32


class MessageType(str, Enum):
    """All supported message types in the protocol"""
    # Connection & Registration
    REGISTER = "register"
    USER_JOINED = "user_joined"
    USER_LEFT = "user_left"
    ONLINE_USERS = "online_users"
    
    # Chat
    CHAT_MESSAGE = "chat_message"
    TYPING_STATUS = "typing_status"
    
    # AI - Server-side processing
    AI_ANALYSIS_REQUEST = "ai_analysis_request"
    AI_SUGGESTION = "ai_suggestion"
    AI_EMOTION = "ai_emotion"
    AI_MEMORY = "ai_memory"
    
    # Legacy AI - for backward compatibility
    AI_REQUEST = "ai_request"  # Old client request format

    # Heartbeat
    PING = "ping"
    PONG = "pong"


@dataclass
class AIAnalysisRequest:
    """
    Client request for AI analysis.
    Includes context_snapshot for server cold-start recovery.
    """
    conversation_id: str
    sender_id: str
    sender_name: str
    # Context snapshot: recent messages for cold-start recovery
    # Server uses this if its session is empty or stale
    context_snapshot: Optional[List[Dict[str, Any]]] = None
    
    def to_dict(self) -> Dict:
        return {
            "type": MessageType.AI_ANALYSIS_REQUEST.value,
            "conversation_id": self.conversation_id,
            "sender_id": self.sender_id,
            "sender_name": self.sender_name,
            "context_snapshot": self.context_snapshot or []
        }


@dataclass 
class AISuggestion:
    """Server response with AI-generated suggestion"""
    conversation_id: str
    title: str
    content: str
    suggestion_type: str = "suggestion"  # plan/schedule/checklist/suggestion
    
    def to_dict(self) -> Dict:
        return {
            "type": MessageType.AI_SUGGESTION.value,
            "conversation_id": self.conversation_id,
            "title": self.title,
            "content": self.content,
            "suggestion_type": self.suggestion_type
        }


@dataclass
class AIEmotion:
    """Server response with emotion analysis"""
    conversation_id: str
    scores: Dict[str, float]  # {"neutral": 0.5, "happy": 0.3, ...}
    
    def to_dict(self) -> Dict:
        return {
            "type": MessageType.AI_EMOTION.value,
            "conversation_id": self.conversation_id,
            "scores": self.scores
        }


@dataclass
class AIMemory:
    """Server response with extracted memories"""
    conversation_id: str
    memories: List[Dict[str, str]]  # [{"content": "...", "category": "..."}]
    
    def to_dict(self) -> Dict:
        return {
            "type": MessageType.AI_MEMORY.value,
            "conversation_id": self.conversation_id,
            "memories": self.memories
        }


class Protocol:
    """Protocol utilities for packing/unpacking messages"""
    
    HEADER_SIZE = HEADER_SIZE
    
    @staticmethod
    def pack(data: Dict) -> bytes:
        """Pack a message dict with length header and CRC32 checksum"""
        payload = json.dumps(data, ensure_ascii=False).encode('utf-8')
        length = len(payload)
        checksum = zlib.crc32(payload) & 0xFFFFFFFF
        header = struct.pack('>II', length, checksum)
        return header + payload
    
    @staticmethod
    def unpack_header(header_bytes: bytes) -> Tuple[int, int]:
        """Unpack header to get (length, crc32)"""
        return struct.unpack('>II', header_bytes)
    
    @staticmethod
    def verify_crc(payload: bytes, expected_crc: int) -> bool:
        """Verify CRC32 checksum"""
        return (zlib.crc32(payload) & 0xFFFFFFFF) == expected_crc
    
    @staticmethod
    def parse_message(payload: bytes) -> Optional[Dict]:
        """Parse JSON payload to dict"""
        try:
            return json.loads(payload.decode('utf-8'))
        except json.JSONDecodeError:
            return None


# Convenience functions for backward compatibility with existing code
def pack_message(data: dict) -> bytes:
    """Pack a message with length header and CRC32"""
    return Protocol.pack(data)


def unpack_header(header_bytes: bytes) -> tuple:
    """Unpack header to get (length, crc32)"""
    return Protocol.unpack_header(header_bytes)


def verify_crc(payload: bytes, expected_crc: int) -> bool:
    """Verify CRC32 checksum"""
    return Protocol.verify_crc(payload, expected_crc)
