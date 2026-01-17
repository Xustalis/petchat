"""Data models for pet-chat application"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List
import uuid


def generate_uuid() -> str:
    """Generate a new UUID string"""
    return str(uuid.uuid4())


@dataclass
class User:
    """Represents a chat user"""
    id: str  # UUID string
    name: str
    avatar: str = ""
    ip_address: str = ""
    port: int = 0
    last_seen: Optional[datetime] = None
    is_online: bool = False
    
    @classmethod
    def create_local(cls, name: str, avatar: str = "") -> "User":
        """Create a new local user with generated UUID"""
        return cls(
            id=generate_uuid(),
            name=name,
            avatar=avatar,
            is_online=True
        )
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization"""
        return {
            "id": self.id,
            "name": self.name,
            "avatar": self.avatar,
            "ip_address": self.ip_address,
            "port": self.port,
            "last_seen": self.last_seen.isoformat() if self.last_seen else None,
            "is_online": self.is_online
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "User":
        """Create from dictionary"""
        last_seen = data.get("last_seen")
        if last_seen and isinstance(last_seen, str):
            last_seen = datetime.fromisoformat(last_seen)
        return cls(
            id=data["id"],
            name=data["name"],
            avatar=data.get("avatar", ""),
            ip_address=data.get("ip_address", ""),
            port=data.get("port", 0),
            last_seen=last_seen,
            is_online=data.get("is_online", False)
        )


@dataclass
class Conversation:
    """Represents a chat conversation/session"""
    id: str  # UUID string
    type: str  # "p2p" or "group"
    name: str  # Display name
    peer_user_id: Optional[str] = None  # For P2P, the other user's ID
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    last_message: str = ""  # Preview of last message
    unread_count: int = 0
    
    @classmethod
    def create_p2p(cls, peer_user: User) -> "Conversation":
        """Create a new P2P conversation with a peer user"""
        now = datetime.now()
        return cls(
            id=generate_uuid(),
            type="p2p",
            name=peer_user.name,
            peer_user_id=peer_user.id,
            created_at=now,
            updated_at=now
        )
    
    @classmethod
    def create_group(cls, name: str) -> "Conversation":
        """Create a new group conversation"""
        now = datetime.now()
        return cls(
            id=generate_uuid(),
            type="group",
            name=name,
            created_at=now,
            updated_at=now
        )
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization"""
        return {
            "id": self.id,
            "type": self.type,
            "name": self.name,
            "peer_user_id": self.peer_user_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "last_message": self.last_message,
            "unread_count": self.unread_count
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Conversation":
        """Create from dictionary"""
        created_at = data.get("created_at")
        updated_at = data.get("updated_at")
        if created_at and isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        if updated_at and isinstance(updated_at, str):
            updated_at = datetime.fromisoformat(updated_at)
        return cls(
            id=data["id"],
            type=data["type"],
            name=data["name"],
            peer_user_id=data.get("peer_user_id"),
            created_at=created_at,
            updated_at=updated_at,
            last_message=data.get("last_message", ""),
            unread_count=data.get("unread_count", 0)
        )


@dataclass
class Message:
    """Represents a chat message"""
    id: Optional[int] = None  # Database ID
    conversation_id: str = ""
    sender_id: str = ""
    sender_name: str = ""
    content: str = ""
    timestamp: Optional[datetime] = None
    
    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "conversation_id": self.conversation_id,
            "sender_id": self.sender_id,
            "sender_name": self.sender_name,
            "content": self.content,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None
        }
