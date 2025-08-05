"""
Session management for maintaining chat conversation history.
"""

import asyncio
import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pathlib import Path
from abc import ABC, abstractmethod

from app.core.chat_models.base import ChatMessage


class BaseSessionStorage(ABC):
    """Abstract base class for session storage backends"""
    
    @abstractmethod
    async def save_session(self, session_id: str, session_data: Dict[str, Any]) -> None:
        """Save session data"""
        pass
    
    @abstractmethod
    async def load_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Load session data"""
        pass
    
    @abstractmethod
    async def delete_session(self, session_id: str) -> None:
        """Delete session data"""
        pass
    
    @abstractmethod
    async def list_sessions(self, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all sessions, optionally filtered by user_id"""
        pass
    
    @abstractmethod
    async def cleanup_expired_sessions(self, max_age: timedelta) -> int:
        """Clean up expired sessions, return count of deleted sessions"""
        pass


class InMemorySessionStorage(BaseSessionStorage):
    """In-memory session storage (for development/testing)"""
    
    def __init__(self):
        self._sessions: Dict[str, Dict[str, Any]] = {}
        self._lock = asyncio.Lock()
    
    async def save_session(self, session_id: str, session_data: Dict[str, Any]) -> None:
        """Save session data to memory"""
        async with self._lock:
            self._sessions[session_id] = session_data.copy()
    
    async def load_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Load session data from memory"""
        async with self._lock:
            return self._sessions.get(session_id)
    
    async def delete_session(self, session_id: str) -> None:
        """Delete session from memory"""
        async with self._lock:
            self._sessions.pop(session_id, None)
    
    async def list_sessions(self, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """List sessions from memory"""
        async with self._lock:
            sessions = []
            for session_id, data in self._sessions.items():
                if user_id is None or data.get("user_id") == user_id:
                    sessions.append({
                        "session_id": session_id,
                        **data
                    })
            return sessions
    
    async def cleanup_expired_sessions(self, max_age: timedelta) -> int:
        """Clean up expired sessions from memory"""
        cutoff_time = datetime.utcnow() - max_age
        expired_sessions = []
        
        async with self._lock:
            for session_id, data in self._sessions.items():
                last_activity = datetime.fromisoformat(data.get("last_activity", "1970-01-01T00:00:00"))
                if last_activity < cutoff_time:
                    expired_sessions.append(session_id)
            
            for session_id in expired_sessions:
                del self._sessions[session_id]
        
        return len(expired_sessions)


class FileSessionStorage(BaseSessionStorage):
    """File-based session storage"""
    
    def __init__(self, storage_dir: str = "sessions"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(exist_ok=True)
        self._lock = asyncio.Lock()
    
    def _get_session_file(self, session_id: str) -> Path:
        """Get the file path for a session"""
        return self.storage_dir / f"{session_id}.json"
    
    async def save_session(self, session_id: str, session_data: Dict[str, Any]) -> None:
        """Save session data to file"""
        session_file = self._get_session_file(session_id)
        
        async with self._lock:
            try:
                with open(session_file, 'w') as f:
                    json.dump(session_data, f, indent=2, default=str)
            except Exception as e:
                raise RuntimeError(f"Failed to save session {session_id}: {str(e)}")
    
    async def load_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Load session data from file"""
        session_file = self._get_session_file(session_id)
        
        if not session_file.exists():
            return None
        
        async with self._lock:
            try:
                with open(session_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                raise RuntimeError(f"Failed to load session {session_id}: {str(e)}")
    
    async def delete_session(self, session_id: str) -> None:
        """Delete session file"""
        session_file = self._get_session_file(session_id)
        
        async with self._lock:
            try:
                if session_file.exists():
                    session_file.unlink()
            except Exception as e:
                raise RuntimeError(f"Failed to delete session {session_id}: {str(e)}")
    
    async def list_sessions(self, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """List sessions from files"""
        sessions = []
        
        async with self._lock:
            for session_file in self.storage_dir.glob("*.json"):
                try:
                    with open(session_file, 'r') as f:
                        data = json.load(f)
                    
                    if user_id is None or data.get("user_id") == user_id:
                        sessions.append({
                            "session_id": session_file.stem,
                            **data
                        })
                except Exception:
                    continue  # Skip corrupted files
        
        return sessions
    
    async def cleanup_expired_sessions(self, max_age: timedelta) -> int:
        """Clean up expired session files"""
        cutoff_time = datetime.utcnow() - max_age
        deleted_count = 0
        
        async with self._lock:
            for session_file in self.storage_dir.glob("*.json"):
                try:
                    with open(session_file, 'r') as f:
                        data = json.load(f)
                    
                    last_activity = datetime.fromisoformat(data.get("last_activity", "1970-01-01T00:00:00"))
                    if last_activity < cutoff_time:
                        session_file.unlink()
                        deleted_count += 1
                        
                except Exception:
                    continue  # Skip corrupted files
        
        return deleted_count


class ChatSession:
    """Represents a single chat session"""
    
    def __init__(self, session_id: str, user_id: Optional[str] = None, title: Optional[str] = None):
        self.session_id = session_id
        self.user_id = user_id
        self.title = title or "New Chat"
        self.messages: List[ChatMessage] = []
        self.created_at = datetime.utcnow()
        self.last_activity = self.created_at
        self.metadata: Dict[str, Any] = {}
    
    def add_message(self, message: ChatMessage) -> None:
        """Add a message to the session"""
        if not message.timestamp:
            message.timestamp = datetime.utcnow().isoformat()
        
        self.messages.append(message)
        self.last_activity = datetime.utcnow()
        
        # Auto-generate title from first user message
        if not self.title or self.title == "New Chat":
            if message.role == "user" and len(self.messages) <= 2:
                self.title = self._generate_title(message.content)
    
    def get_recent_messages(self, limit: int = 10) -> List[ChatMessage]:
        """Get recent messages from the session"""
        return self.messages[-limit:] if self.messages else []
    
    def get_context_messages(self, context_length: int = 4000) -> List[ChatMessage]:
        """Get messages that fit within context length"""
        # Simple approach: estimate tokens as characters/4 and work backwards
        estimated_tokens = 0
        context_messages = []
        
        for message in reversed(self.messages):
            message_tokens = len(message.content) // 4  # Rough estimation
            if estimated_tokens + message_tokens > context_length:
                break
            
            context_messages.insert(0, message)
            estimated_tokens += message_tokens
        
        return context_messages
    
    def _generate_title(self, content: str) -> str:
        """Generate a title from message content"""
        # Take first 50 characters and clean up
        title = content[:50].strip()
        if len(content) > 50:
            title += "..."
        return title
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert session to dictionary"""
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "title": self.title,
            "messages": [
                {
                    "role": msg.role,
                    "content": msg.content,
                    "timestamp": msg.timestamp,
                    "metadata": msg.metadata
                }
                for msg in self.messages
            ],
            "created_at": self.created_at.isoformat(),
            "last_activity": self.last_activity.isoformat(),
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ChatSession":
        """Create session from dictionary"""
        session = cls(
            session_id=data["session_id"],
            user_id=data.get("user_id"),
            title=data.get("title", "New Chat")
        )
        
        session.messages = [
            ChatMessage(
                role=msg["role"],
                content=msg["content"],
                timestamp=msg.get("timestamp"),
                metadata=msg.get("metadata")
            )
            for msg in data.get("messages", [])
        ]
        
        session.created_at = datetime.fromisoformat(data.get("created_at", datetime.utcnow().isoformat()))
        session.last_activity = datetime.fromisoformat(data.get("last_activity", datetime.utcnow().isoformat()))
        session.metadata = data.get("metadata", {})
        
        return session


class SessionManager:
    """Manages chat sessions with configurable storage backend"""
    
    def __init__(self, storage: Optional[BaseSessionStorage] = None):
        self.storage = storage or InMemorySessionStorage()
        self._cleanup_task: Optional[asyncio.Task] = None
        self._cleanup_interval = timedelta(hours=1)
        self._max_session_age = timedelta(days=30)
    
    async def start_cleanup_task(self):
        """Start the background cleanup task"""
        if self._cleanup_task is None or self._cleanup_task.done():
            self._cleanup_task = asyncio.create_task(self._periodic_cleanup())
    
    async def stop_cleanup_task(self):
        """Stop the background cleanup task"""
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
    
    async def _periodic_cleanup(self):
        """Periodic cleanup of expired sessions"""
        while True:
            try:
                await asyncio.sleep(self._cleanup_interval.total_seconds())
                deleted_count = await self.storage.cleanup_expired_sessions(self._max_session_age)
                if deleted_count > 0:
                    print(f"Cleaned up {deleted_count} expired sessions")
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Error during session cleanup: {e}")
    
    async def create_session(self, user_id: Optional[str] = None, title: Optional[str] = None) -> ChatSession:
        """Create a new chat session"""
        session_id = str(uuid.uuid4())
        session = ChatSession(session_id, user_id, title)
        await self.storage.save_session(session_id, session.to_dict())
        return session
    
    async def get_session(self, session_id: str) -> Optional[ChatSession]:
        """Get an existing chat session"""
        session_data = await self.storage.load_session(session_id)
        if session_data:
            return ChatSession.from_dict(session_data)
        return None
    
    async def save_session(self, session: ChatSession) -> None:
        """Save a chat session"""
        await self.storage.save_session(session.session_id, session.to_dict())
    
    async def delete_session(self, session_id: str) -> None:
        """Delete a chat session"""
        await self.storage.delete_session(session_id)
    
    async def list_sessions(self, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all sessions, optionally filtered by user_id"""
        return await self.storage.list_sessions(user_id)
    
    async def add_message_to_session(self, session_id: str, message: ChatMessage) -> Optional[ChatSession]:
        """Add a message to an existing session"""
        session = await self.get_session(session_id)
        if session:
            session.add_message(message)
            await self.save_session(session)
            return session
        return None