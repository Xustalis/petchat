"""Database module for storing chat history and memories"""
import sqlite3
from datetime import datetime
from typing import List, Dict, Optional
import os


class Database:
    """SQLite database manager for chat records and memories"""
    
    def __init__(self, db_path: str = "petchat.db"):
        """Initialize database connection"""
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_tables()
    
    def _init_tables(self):
        """Create necessary tables if they don't exist"""
        cursor = self.conn.cursor()
        
        # Chat messages table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sender TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                session_id TEXT DEFAULT 'default'
            )
        """)
        
        # Memories table (key information extracted from conversations)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT NOT NULL,
                category TEXT,
                created_at TEXT NOT NULL,
                session_id TEXT DEFAULT 'default'
            )
        """)
        
        # Emotions history table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS emotions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                emotion_type TEXT NOT NULL,
                confidence REAL,
                context TEXT,
                timestamp TEXT NOT NULL,
                session_id TEXT DEFAULT 'default'
            )
        """)
        
        self.conn.commit()
    
    def add_message(self, sender: str, content: str, session_id: str = 'default'):
        """Add a new message to the database"""
        cursor = self.conn.cursor()
        timestamp = datetime.now().isoformat()
        cursor.execute(
            "INSERT INTO messages (sender, content, timestamp, session_id) VALUES (?, ?, ?, ?)",
            (sender, content, timestamp, session_id)
        )
        self.conn.commit()
        return cursor.lastrowid
    
    def get_recent_messages(self, limit: int = 10, session_id: str = 'default') -> List[Dict]:
        """Get recent messages"""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT sender, content, timestamp FROM messages WHERE session_id = ? ORDER BY timestamp DESC LIMIT ?",
            (session_id, limit)
        )
        rows = cursor.fetchall()
        # Return in chronological order (oldest first)
        return [dict(row) for row in reversed(rows)]
    
    def add_memory(self, content: str, category: Optional[str] = None, session_id: str = 'default'):
        """Add a memory (extracted key information)"""
        cursor = self.conn.cursor()
        timestamp = datetime.now().isoformat()
        cursor.execute(
            "INSERT INTO memories (content, category, created_at, session_id) VALUES (?, ?, ?, ?)",
            (content, category, timestamp, session_id)
        )
        self.conn.commit()
        return cursor.lastrowid
    
    def get_memories(self, session_id: str = 'default') -> List[Dict]:
        """Get all memories"""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT content, category, created_at FROM memories WHERE session_id = ? ORDER BY created_at DESC",
            (session_id,)
        )
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    
    def add_emotion(self, emotion_type: str, confidence: float, context: Optional[str] = None, session_id: str = 'default'):
        """Record emotion analysis result"""
        cursor = self.conn.cursor()
        timestamp = datetime.now().isoformat()
        cursor.execute(
            "INSERT INTO emotions (emotion_type, confidence, context, timestamp, session_id) VALUES (?, ?, ?, ?, ?)",
            (emotion_type, confidence, context, timestamp, session_id)
        )
        self.conn.commit()
        return cursor.lastrowid
    
    def clear_memories(self, session_id: str = 'default'):
        """Clear all memories for a session"""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM memories WHERE session_id = ?", (session_id,))
        self.conn.commit()
    
    def close(self):
        """Close database connection"""
        self.conn.close()

