import uuid
import asyncio
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from app.config.settings import settings


class MongoChatStore:
    """MongoDB-backed store for users and conversation-centric chat with summaries."""

    def __init__(self, uri: str, db_name: str):
        self.client = AsyncIOMotorClient(uri)
        self.db: AsyncIOMotorDatabase = self.client[db_name]

    # ---------- User management for Keycloak integration ----------
    async def ensure_user_exists(self, user_id: str, username: str, email: str) -> Dict[str, Any]:
        """Ensure user exists in our database (for Keycloak users)."""
        existing = await self.db.users.find_one({"user_id": user_id})
        if existing:
            # Update user info if needed
            await self.db.users.update_one(
                {"user_id": user_id},
                {"$set": {
                    "username": username,
                    "email": email,
                    "last_login": datetime.utcnow().isoformat()
                }}
            )
            return existing
        
        # Create new user record
        doc = {
            "user_id": user_id,
            "username": username,
            "email": email,
            "created_at": datetime.utcnow().isoformat(),
            "last_login": datetime.utcnow().isoformat()
        }
        await self.db.users.insert_one(doc)
        return {"user_id": user_id, "username": username, "email": email}

    async def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        return await self.db.users.find_one({"user_id": user_id}, {"_id": 0, "password_hash": 0})

    # ---------- Conversations ----------
    async def create_conversation(self, user_id: str, title: str = "New Chat", token_limit: int = 128_000) -> str:
        conversation_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        doc = {
            "conversation_id": conversation_id,
            "user_id": user_id,
            "title": title or "New Chat",
            "created_at": now,
            "last_activity": now,
            "token_limit": int(token_limit),
            "token_count_total": 0,
        }
        await self.db.conversations.insert_one(doc)
        return conversation_id

    async def list_conversations(self, user_id: str) -> List[Dict[str, Any]]:
        cursor = self.db.conversations.find({"user_id": user_id}, {"_id": 0}).sort("last_activity", -1)
        return [doc async for doc in cursor]

    async def get_conversation(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        return await self.db.conversations.find_one({"conversation_id": conversation_id}, {"_id": 0})

    async def update_conversation_title_if_default(self, conversation_id: str, inferred_title: str) -> None:
        if not inferred_title:
            return
        await self.db.conversations.update_one(
            {"conversation_id": conversation_id, "$or": [{"title": {"$exists": False}}, {"title": "New Chat"}, {"title": ""}]},
            {"$set": {"title": inferred_title[:100]}}
        )

    # ---------- Token utilities ----------
    @staticmethod
    def estimate_tokens(text: str) -> int:
        if not text:
            return 0
        # Simple heuristic: ~4 chars per token
        return max(1, len(text) // 4)

    # ---------- Messages (conversation-based) ----------
    async def add_message(self, conversation_id: str, role: str, content: str, token_count: Optional[int] = None) -> None:
        message_id = str(uuid.uuid4())
        doc = {
            "message_id": message_id,
            "conversation_id": conversation_id,
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow().isoformat(),
            "token_count": token_count if token_count is not None else self.estimate_tokens(content),
        }
        await self.db.messages.insert_one(doc)
        # update conversation last_activity, counts
        await self.db.conversations.update_one(
            {"conversation_id": conversation_id},
            {
                "$set": {"last_activity": doc["timestamp"]},
                "$inc": {"message_count": 1, "token_count_total": int(doc["token_count"])},
            },
        )

    async def add_message_pair(self, conversation_id: str, user_content: str, assistant_content: str) -> None:
        now_iso = datetime.utcnow().isoformat()
        user_tokens = self.estimate_tokens(user_content)
        assistant_tokens = self.estimate_tokens(assistant_content)
        user_doc = {
            "message_id": str(uuid.uuid4()),
            "conversation_id": conversation_id,
            "role": "user",
            "content": user_content,
            "timestamp": now_iso,
            "token_count": user_tokens,
        }
        assistant_doc = {
            "message_id": str(uuid.uuid4()),
            "conversation_id": conversation_id,
            "role": "assistant",
            "content": assistant_content,
            "timestamp": datetime.utcnow().isoformat(),
            "token_count": assistant_tokens,
        }
        await self.db.messages.insert_many([user_doc, assistant_doc])
        await self.db.conversations.update_one(
            {"conversation_id": conversation_id},
            {
                "$set": {"last_activity": assistant_doc["timestamp"]},
                "$inc": {"message_count": 2, "token_count_total": int(user_tokens + assistant_tokens)},
            },
        )

    async def get_last_messages(self, conversation_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        # Fetch up to 'limit' latest messages in ascending order
        if limit and limit > 0:
            cursor = (
                self.db.messages.find({"conversation_id": conversation_id}, {"_id": 0})
                .sort("timestamp", -1)
                .limit(limit)
            )
            latest_desc = [doc async for doc in cursor]
            messages = list(reversed(latest_desc))
        else:
            cursor = (
                self.db.messages.find({"conversation_id": conversation_id}, {"_id": 0})
                .sort("timestamp", 1)
            )
            messages = [doc async for doc in cursor]
        return messages

    # ---------- Summaries ----------
    async def list_summaries(self, conversation_id: str) -> List[Dict[str, Any]]:
        cursor = self.db.summaries.find({"conversation_id": conversation_id}, {"_id": 0}).sort([("layer", 1), ("created_at", 1)])
        return [doc async for doc in cursor]

    async def add_summary(self, conversation_id: str, layer: int, summary_text: str, token_count: Optional[int] = None) -> None:
        doc = {
            "summary_id": str(uuid.uuid4()),
            "conversation_id": conversation_id,
            "layer": int(layer),
            "summary_text": summary_text,
            "token_count": token_count if token_count is not None else self.estimate_tokens(summary_text),
            "created_at": datetime.utcnow().isoformat(),
        }
        await self.db.summaries.insert_one(doc)
        await self.db.conversations.update_one(
            {"conversation_id": conversation_id},
            {"$inc": {"token_count_total": int(doc["token_count"])}}
        )

    async def delete_messages(self, conversation_id: str, message_ids: List[str]) -> None:
        if not message_ids:
            return
        # Reduce token_count_total accordingly
        msgs = await self.db.messages.find({"message_id": {"$in": message_ids}}, {"token_count": 1, "conversation_id": 1, "_id": 0}).to_list(length=None)
        total_reduce = sum(int(m.get("token_count", 0)) for m in msgs)
        await self.db.messages.delete_many({"message_id": {"$in": message_ids}})
        await self.db.conversations.update_one(
            {"conversation_id": conversation_id},
            {"$inc": {"token_count_total": -int(total_reduce)}}
        )

    async def get_token_totals(self, conversation_id: str) -> int:
        convo = await self.get_conversation(conversation_id)
        return int(convo.get("token_count_total", 0)) if convo else 0

    async def summarize_if_needed(self, conversation_id: str, token_limit: int, target_ratio: float, chat_model) -> None:
        try:
            convo = await self.get_conversation(conversation_id)
            if not convo:
                return
            current_total = int(convo.get("token_count_total", 0))
            if current_total <= token_limit:
                return

            target_total = int(token_limit * float(target_ratio))
            # Collect candidates: oldest plain messages (exclude summaries collection)
            cursor = self.db.messages.find({"conversation_id": conversation_id}, {"_id": 0}).sort("timestamp", 1)
            msgs = [m async for m in cursor]
            to_summarize: List[Dict[str, Any]] = []
            accumulated = 0
            reduce_needed = current_total - target_total
            for m in msgs:
                to_summarize.append(m)
                accumulated += int(m.get("token_count", self.estimate_tokens(m.get("content", ""))))
                if accumulated >= reduce_needed:
                    break

            if not to_summarize:
                return

            # Build summary prompt
            def build_transcript(items: List[Dict[str, Any]]) -> str:
                parts = []
                for it in items:
                    role = it.get("role", "user")
                    content = it.get("content", "")
                    parts.append(f"{role.capitalize()}: {content}")
                return "\n".join(parts)

            transcript = build_transcript(to_summarize)
            system_prompt = (
                "You are a conversation summarizer. Summarize the following messages into a concise, factual summary "
                "that preserves all important information, decisions, constraints, names, numbers, and references. "
                "Write neutrally as a single paragraph."
            )

            # Call LLM via LangChain chat_model
            try:
                from langchain.schema import SystemMessage, HumanMessage
                summary_resp = await asyncio.to_thread(
                    chat_model.invoke,
                    [SystemMessage(content=system_prompt), HumanMessage(content=transcript)]
                )
                summary_text = summary_resp.content if hasattr(summary_resp, "content") else str(summary_resp)
            except Exception:
                # Fallback: naive truncation
                summary_text = transcript[:1000]

            summary_tokens = self.estimate_tokens(summary_text)
            # Determine next layer
            existing = await self.list_summaries(conversation_id)
            next_layer = 1
            if existing:
                next_layer = max(int(s.get("layer", 1)) for s in existing)  # base for potential merge below
            # Store summary and delete original messages
            await self.add_summary(conversation_id, layer=1, summary_text=summary_text, token_count=summary_tokens)
            await self.delete_messages(conversation_id, [m["message_id"] for m in to_summarize])

            # If still over limit, merge summaries recursively
            convo_after = await self.get_conversation(conversation_id)
            if int(convo_after.get("token_count_total", 0)) > token_limit:
                await self._merge_summaries_until_within_limit(conversation_id, token_limit, target_ratio, chat_model)
        except Exception as e:
            print(f"summarize_if_needed error: {e}")

    async def _merge_summaries_until_within_limit(self, conversation_id: str, token_limit: int, target_ratio: float, chat_model) -> None:
        # Merge lowest-layer summaries in chronological order until under target
        while True:
            convo = await self.get_conversation(conversation_id)
            if not convo:
                return
            total = int(convo.get("token_count_total", 0))
            if total <= token_limit:
                return
            target_total = int(token_limit * float(target_ratio))
            reduce_needed = total - target_total

            summaries = await self.list_summaries(conversation_id)
            if not summaries:
                return
            lowest_layer = min(int(s.get("layer", 1)) for s in summaries)
            layer_summaries = [s for s in summaries if int(s.get("layer", 1)) == lowest_layer]
            if len(layer_summaries) < 2:
                return
            # Merge oldest ones until sufficient reduction
            layer_summaries.sort(key=lambda x: x.get("created_at", ""))
            merge_batch: List[Dict[str, Any]] = []
            acc = 0
            for s in layer_summaries:
                merge_batch.append(s)
                acc += int(s.get("token_count", 0))
                if acc >= reduce_needed:
                    break
            if not merge_batch:
                return
            merged_text = "\n\n".join(s.get("summary_text", "") for s in merge_batch)
            system_prompt = (
                "You are a conversation summarizer. Merge the following summaries into a single, even more concise "
                "summary that keeps all critical details for future context."
            )
            try:
                from langchain.schema import SystemMessage, HumanMessage
                merged_resp = await asyncio.to_thread(
                    chat_model.invoke,
                    [SystemMessage(content=system_prompt), HumanMessage(content=merged_text)]
                )
                merged = merged_resp.content if hasattr(merged_resp, "content") else str(merged_resp)
            except Exception:
                merged = merged_text[:1000]
            merged_tokens = self.estimate_tokens(merged)

            # Insert higher-layer summary
            new_layer = lowest_layer + 1
            await self.add_summary(conversation_id, new_layer, merged, merged_tokens)
            # Remove merged lower-layer summaries and reduce totals accordingly
            ids = [s.get("summary_id") for s in merge_batch if s.get("summary_id")]
            reduce = sum(int(s.get("token_count", 0)) for s in merge_batch)
            if ids:
                await self.db.summaries.delete_many({"summary_id": {"$in": ids}})
                await self.db.conversations.update_one(
                    {"conversation_id": conversation_id},
                    {"$inc": {"token_count_total": -int(reduce)}}
                )

    # ---------- RAG Prompt Management ----------
    async def create_rag_prompt(self, user_id: str, name: str, content: str, set_active: bool = False) -> Dict[str, Any]:
        pid = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        doc = {
            "prompt_id": pid,
            "user_id": user_id,
            "name": name,
            "content": content,
            "is_active": bool(set_active),
            "created_at": now,
            "updated_at": None,
        }
        if set_active:
            await self.db.rag_prompts.update_many({"user_id": user_id}, {"$set": {"is_active": False}})
        await self.db.rag_prompts.insert_one(doc)
        return {"prompt_id": pid}

    async def list_rag_prompts(self, user_id: str) -> List[Dict[str, Any]]:
        cursor = self.db.rag_prompts.find({"user_id": user_id}, {"_id": 0}).sort("created_at", -1)
        return [doc async for doc in cursor]

    async def get_active_rag_prompt(self, user_id: str) -> Optional[Dict[str, Any]]:
        return await self.db.rag_prompts.find_one({"user_id": user_id, "is_active": True}, {"_id": 0})

    async def set_active_rag_prompt(self, user_id: str, prompt_id: str) -> None:
        await self.db.rag_prompts.update_many({"user_id": user_id}, {"$set": {"is_active": False}})
        await self.db.rag_prompts.update_one({"user_id": user_id, "prompt_id": prompt_id}, {"$set": {"is_active": True}})

    async def update_rag_prompt(self, user_id: str, prompt_id: str, updates: Dict[str, Any]) -> None:
        updates = {k: v for k, v in updates.items() if v is not None}
        if not updates:
            return
        updates["updated_at"] = datetime.utcnow().isoformat()
        await self.db.rag_prompts.update_one({"user_id": user_id, "prompt_id": prompt_id}, {"$set": updates})

    async def delete_rag_prompt(self, user_id: str, prompt_id: str) -> None:
        await self.db.rag_prompts.delete_one({"user_id": user_id, "prompt_id": prompt_id})


# Global accessor
mongo_store: Optional[MongoChatStore] = None


def get_mongo_store() -> MongoChatStore:
    global mongo_store
    if mongo_store is None:
        print(f"DEBUG: Initializing MongoDB store with URI: {settings.mongodb_uri}")
        print(f"DEBUG: MongoDB database name: {settings.mongodb_db_name}")
        try:
            mongo_store = MongoChatStore(settings.mongodb_uri, settings.mongodb_db_name)
            print("DEBUG: MongoDB store initialized successfully")
        except Exception as e:
            print(f"DEBUG: Error initializing MongoDB store: {str(e)}")
            raise
    return mongo_store


