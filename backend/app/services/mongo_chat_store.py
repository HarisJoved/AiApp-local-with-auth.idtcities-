import uuid
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from passlib.context import CryptContext
from jose import jwt

from app.config.settings import settings


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class MongoChatStore:
    """MongoDB-backed store for users, topics, sessions, and messages."""

    def __init__(self, uri: str, db_name: str):
        self.client = AsyncIOMotorClient(uri)
        self.db: AsyncIOMotorDatabase = self.client[db_name]

    # ---------- Auth helpers ----------
    @staticmethod
    def hash_password(password: str) -> str:
        return pwd_context.hash(password)

    @staticmethod
    def verify_password(password: str, password_hash: str) -> bool:
        return pwd_context.verify(password, password_hash)

    @staticmethod
    def create_access_token(data: dict, expires_minutes: int) -> str:
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(minutes=expires_minutes)
        to_encode.update({"exp": expire})
        return jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)

    # ---------- Users ----------
    async def create_user(self, username: str, password: str) -> Dict[str, Any]:
        existing = await self.db.users.find_one({"username": username})
        if existing:
            raise ValueError("Username already exists")
        user_id = str(uuid.uuid4())
        doc = {
            "user_id": user_id,
            "username": username,
            "password_hash": self.hash_password(password),
            "created_at": datetime.utcnow().isoformat(),
        }
        await self.db.users.insert_one(doc)
        return {"user_id": user_id, "username": username, "created_at": doc["created_at"]}

    async def authenticate_user(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        user = await self.db.users.find_one({"username": username})
        if not user:
            return None
        if not self.verify_password(password, user.get("password_hash", "")):
            return None
        return {"user_id": user["user_id"], "username": user["username"]}

    async def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        return await self.db.users.find_one({"user_id": user_id}, {"_id": 0, "password_hash": 0})

    # ---------- Topics ----------
    async def create_topic(self, user_id: str, title: str) -> str:
        topic_id = str(uuid.uuid4())
        doc = {
            "topic_id": topic_id,
            "user_id": user_id,
            "title": title or "Chat",
            "created_at": datetime.utcnow().isoformat(),
            "last_activity": datetime.utcnow().isoformat(),
        }
        await self.db.topics.insert_one(doc)
        return topic_id

    async def list_topics(self, user_id: str) -> List[Dict[str, Any]]:
        cursor = self.db.topics.find({"user_id": user_id}, {"_id": 0})
        return [doc async for doc in cursor]

    async def get_or_create_default_topic(self, user_id: str, inferred_title: Optional[str] = None) -> str:
        # Reuse most recently active topic if present
        doc = await self.db.topics.find_one({"user_id": user_id}, sort=[("last_activity", -1)])
        if doc and doc.get("topic_id"):
            return doc["topic_id"]
        # Otherwise create a new topic with an inferred or generic title
        return await self.create_topic(user_id, inferred_title or "General")

    # ---------- Sessions ----------
    async def create_session(self, user_id: str, topic_id: str, title: str) -> str:
        session_id = str(uuid.uuid4())
        doc = {
            "session_id": session_id,
            "user_id": user_id,
            "topic_id": topic_id,
            "title": title,
            "created_at": datetime.utcnow().isoformat(),
            "last_activity": datetime.utcnow().isoformat(),
            "message_count": 0,
        }
        await self.db.sessions.insert_one(doc)
        # bump topic last_activity
        await self.db.topics.update_one({"topic_id": topic_id}, {"$set": {"last_activity": doc["last_activity"]}})
        return session_id

    async def list_sessions(self, user_id: str, topic_id: Optional[str] = None) -> List[Dict[str, Any]]:
        query: Dict[str, Any] = {"user_id": user_id}
        if topic_id:
            query["topic_id"] = topic_id
        cursor = self.db.sessions.find(query, {"_id": 0})
        return [doc async for doc in cursor]

    async def update_session_title_if_default(self, session_id: str, inferred_title: str) -> None:
        if not inferred_title:
            return
        await self.db.sessions.update_one(
            {"session_id": session_id, "$or": [{"title": {"$exists": False}}, {"title": "New Chat"}, {"title": ""}]},
            {"$set": {"title": inferred_title[:100]}}
        )

    # ---------- Messages ----------
    async def add_message(self, session_id: str, role: str, content: str) -> None:
        message_id = str(uuid.uuid4())
        doc = {
            "message_id": message_id,
            "session_id": session_id,
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow().isoformat(),
        }
        await self.db.messages.insert_one(doc)
        # update session last_activity and count
        await self.db.sessions.update_one(
            {"session_id": session_id},
            {"$set": {"last_activity": doc["timestamp"]}, "$inc": {"message_count": 1}},
        )

    async def add_message_pair(self, session_id: str, user_content: str, assistant_content: str) -> None:
        now_iso = datetime.utcnow().isoformat()
        user_doc = {
            "message_id": str(uuid.uuid4()),
            "session_id": session_id,
            "role": "user",
            "content": user_content,
            "timestamp": now_iso,
        }
        assistant_doc = {
            "message_id": str(uuid.uuid4()),
            "session_id": session_id,
            "role": "assistant",
            "content": assistant_content,
            "timestamp": datetime.utcnow().isoformat(),
        }
        await self.db.messages.insert_many([user_doc, assistant_doc])
        await self.db.sessions.update_one(
            {"session_id": session_id},
            {"$set": {"last_activity": assistant_doc["timestamp"]}, "$inc": {"message_count": 2}},
        )

    async def get_last_messages(self, session_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        # Fetch up to 'limit' latest messages in ascending order
        if limit and limit > 0:
            cursor = (
                self.db.messages.find({"session_id": session_id}, {"_id": 0})
                .sort("timestamp", -1)
                .limit(limit)
            )
            latest_desc = [doc async for doc in cursor]
            messages = list(reversed(latest_desc))
        else:
            cursor = (
                self.db.messages.find({"session_id": session_id}, {"_id": 0})
                .sort("timestamp", 1)
            )
            messages = [doc async for doc in cursor]
        return messages


# Global accessor
mongo_store: Optional[MongoChatStore] = None


def get_mongo_store() -> MongoChatStore:
    global mongo_store
    if mongo_store is None:
        mongo_store = MongoChatStore(settings.mongo_uri, settings.mongo_db_name)
    return mongo_store


