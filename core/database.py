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
        
        # Check if users table exists and has correct schema
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
        users_exists = cursor.fetchone() is not None
        
        if users_exists:
            # Check schema
            cursor.execute("PRAGMA table_info(users)")
            user_columns = [col[1] for col in cursor.fetchall()]
            
            if 'id' not in user_columns:
                # Old users table exists - need to migrate
                # Drop old table (it's likely empty or has incompatible data)
                cursor.execute("DROP TABLE users")
                users_exists = False
        
        if not users_exists:
            # Create new users table
            cursor.execute("""
                CREATE TABLE users (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    avatar TEXT,
                    ip_address TEXT,
                    port INTEGER,
                    last_seen TEXT,
                    is_online INTEGER DEFAULT 0
                )
            """)
        
        # Check if conversations table exists and has correct schema
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='conversations'")
        conv_exists = cursor.fetchone() is not None
        
        if conv_exists:
            # Check schema
            cursor.execute("PRAGMA table_info(conversations)")
            conv_columns = [col[1] for col in cursor.fetchall()]
            
            if 'id' not in conv_columns or 'type' not in conv_columns:
                # Old conversations table - drop and recreate
                cursor.execute("DROP TABLE conversations")
                conv_exists = False
        
        if not conv_exists:
            # Create new conversations table
            cursor.execute("""
                CREATE TABLE conversations (
                    id TEXT PRIMARY KEY,
                    type TEXT NOT NULL,
                    name TEXT NOT NULL,
                    peer_user_id TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    last_message TEXT,
                    unread_count INTEGER DEFAULT 0,
                    FOREIGN KEY (peer_user_id) REFERENCES users(id)
                )
            """)
            
            # Create default public chat room
            timestamp = datetime.now().isoformat()
            cursor.execute("""
                INSERT OR IGNORE INTO conversations (id, type, name, created_at, updated_at)
                VALUES ('public', 'group', '公共聊天室', ?, ?)
            """, (timestamp, timestamp))
            print("[DEBUG] Created/verified public chat room")
        
        # Check if messages table needs migration
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='messages'")
        messages_exists = cursor.fetchone() is not None
        
        if messages_exists:
            cursor.execute("PRAGMA table_info(messages)")
            columns = [col[1] for col in cursor.fetchall()]
            
            if 'conversation_id' not in columns:
                # Messages table needs migration from old schema
                # Create new messages table with updated schema
                cursor.execute("""
                    CREATE TABLE messages_new (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        conversation_id TEXT NOT NULL,
                        sender_id TEXT NOT NULL,
                        sender TEXT NOT NULL,
                        content TEXT NOT NULL,
                        timestamp TEXT NOT NULL,
                        FOREIGN KEY (conversation_id) REFERENCES conversations(id),
                        FOREIGN KEY (sender_id) REFERENCES users(id)
                    )
                """)
                
                # Migrate old data to new table (map session_id -> conversation_id)
                # Handle both old schema (with session_id) and very old schema (without it)
                if 'session_id' in columns:
                    cursor.execute("""
                        INSERT INTO messages_new (conversation_id, sender_id, sender, content, timestamp)
                        SELECT 
                            COALESCE(session_id, 'default') as conversation_id,
                            sender as sender_id,
                            sender,
                            content,
                            timestamp
                        FROM messages
                    """)
                else:
                    # Very old schema without session_id
                    cursor.execute("""
                        INSERT INTO messages_new (conversation_id, sender_id, sender, content, timestamp)
                        SELECT 
                            'default' as conversation_id,
                            sender as sender_id,
                            sender,
                            content,
                            timestamp
                        FROM messages
                    """)
                
                # Drop old table and rename new one
                cursor.execute("DROP TABLE messages")
                cursor.execute("ALTER TABLE messages_new RENAME TO messages")
        else:
            # No messages table exists, create new one
            cursor.execute("""
                CREATE TABLE messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    conversation_id TEXT NOT NULL,
                    sender_id TEXT NOT NULL,
                    sender TEXT NOT NULL,
                    content TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    FOREIGN KEY (conversation_id) REFERENCES conversations(id),
                    FOREIGN KEY (sender_id) REFERENCES users(id)
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
    
    
    def add_message(self, sender: str, content: str, conversation_id: str, sender_id: str):
        """Add a new message to the database"""
        cursor = self.conn.cursor()
        timestamp = datetime.now().isoformat()
        cursor.execute(
            "INSERT INTO messages (conversation_id, sender_id, sender, content, timestamp) VALUES (?, ?, ?, ?, ?)",
            (conversation_id, sender_id, sender, content, timestamp)
        )
        self.conn.commit()
        return cursor.lastrowid
    
    
    def get_recent_messages(self, limit: int = 10, conversation_id: str = 'default') -> List[Dict]:
        """Get recent messages for a conversation"""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT sender_id, sender, content, timestamp FROM messages WHERE conversation_id = ? ORDER BY timestamp DESC LIMIT ?",
            (conversation_id, limit)
        )
        rows = cursor.fetchall()
        # Return in chronological order (oldest first)
        return [dict(row) for row in reversed(rows)]
    
    def add_memory(self, content: str, category: Optional[str] = None, session_id: str = 'default') -> Optional[int]:
        """
        Add a memory (extracted key information).
        Returns the memory ID if added, or None if it's a duplicate.
        """
        if not content or not content.strip():
            return None
            
        cursor = self.conn.cursor()
        
        # Check for duplicate content (same content in same session)
        cursor.execute(
            "SELECT id FROM memories WHERE content = ? AND session_id = ?",
            (content.strip(), session_id)
        )
        existing = cursor.fetchone()
        if existing:
            # Duplicate - don't insert
            return None
        
        # Insert new memory
        timestamp = datetime.now().isoformat()
        cursor.execute(
            "INSERT INTO memories (content, category, created_at, session_id) VALUES (?, ?, ?, ?)",
            (content.strip(), category, timestamp, session_id)
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
    
    def deduplicate_memories(self, session_id: str = 'default') -> int:
        """
        Remove duplicate memories, keeping the oldest entry for each unique content.
        Returns the number of duplicates removed.
        """
        cursor = self.conn.cursor()
        
        # Delete duplicates, keeping the one with the smallest ID (oldest)
        cursor.execute("""
            DELETE FROM memories 
            WHERE id NOT IN (
                SELECT MIN(id) 
                FROM memories 
                WHERE session_id = ?
                GROUP BY content
            )
            AND session_id = ?
        """, (session_id, session_id))
        
        removed_count = cursor.rowcount
        self.conn.commit()
        return removed_count
    
    # User management methods
    def upsert_user(self, user_id: str, name: str, avatar: str = "", ip_address: str = "", port: int = 0, is_online: bool = False):
        """Insert or update user information"""
        cursor = self.conn.cursor()
        last_seen = datetime.now().isoformat()
        cursor.execute("""
            INSERT INTO users (id, name, avatar, ip_address, port, last_seen, is_online)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                name = excluded.name,
                avatar = excluded.avatar,
                ip_address = excluded.ip_address,
                port = excluded.port,
                last_seen = excluded.last_seen,
                is_online = excluded.is_online
        """, (user_id, name, avatar, ip_address, port, last_seen, 1 if is_online else 0))
        self.conn.commit()
    
    def get_user(self, user_id: str) -> Optional[Dict]:
        """Get user by ID"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def get_all_users(self) -> List[Dict]:
        """Get all users"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM users ORDER BY last_seen DESC")
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    
    def set_user_online_status(self, user_id: str, is_online: bool):
        """Update user online status"""
        cursor = self.conn.cursor()
        cursor.execute(
            "UPDATE users SET is_online = ?, last_seen = ? WHERE id = ?",
            (1 if is_online else 0, datetime.now().isoformat(), user_id)
        )
        self.conn.commit()
    
    # Conversation management methods
    def create_conversation(self, conv_id: str, conv_type: str, name: str, peer_user_id: Optional[str] = None):
        """Create a new conversation"""
        cursor = self.conn.cursor()
        now = datetime.now().isoformat()
        cursor.execute("""
            INSERT INTO conversations (id, type, name, peer_user_id, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (conv_id, conv_type, name, peer_user_id, now, now))
        self.conn.commit()
    
    def get_conversation(self, conv_id: str) -> Optional[Dict]:
        """Get conversation by ID"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM conversations WHERE id = ?", (conv_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def get_or_create_conversation(self, conversation_id: str, conv_type: str = "p2p", name: str = "") -> Dict:
        """
        Get existing conversation or create new one.
        For P2P: conversation_id is usually peer_user_id
        """
        conv = self.get_conversation(conversation_id)
        if not conv:
            # Create new
            peer_id = conversation_id if conv_type == "p2p" else None
            self.create_conversation(conversation_id, conv_type, name, peer_id)
            conv = self.get_conversation(conversation_id)
            
        return conv
    
    def get_conversations(self) -> List[Dict]:
        """Get all conversations ordered by last update"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM conversations ORDER BY updated_at DESC")
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    
    def update_conversation_last_message(self, conv_id: str, last_message: str):
        """Update the last message preview for a conversation"""
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE conversations 
            SET last_message = ?, updated_at = ?
            WHERE id = ?
        """, (last_message, datetime.now().isoformat(), conv_id))
        self.conn.commit()
    
    def close(self):
        """Close database connection"""
        self.conn.close()

