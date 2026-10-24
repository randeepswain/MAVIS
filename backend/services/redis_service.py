import time
import asyncio
import logging
from typing import Optional, Dict, Any
import redis.asyncio as aioredis
from backend.config import settings

logger = logging.getLogger("mavis.redis")

class InMemoryRedisFallback:
    """
    Robust in-memory fallback that simulates Redis key-value with TTL 
    and queue operations if a standalone Redis instance is not reachable.
    """
    def __init__(self):
        self._store: Dict[str, tuple[str, float]] = {} # key -> (val, expire_at)
        self._queues: Dict[str, list[str]] = {}
        self._lock = asyncio.Lock()

    async def set(self, key: str, value: str, ex: Optional[int] = None, nx: bool = False) -> bool:
        async with self._lock:
            now = time.time()
            if key in self._store:
                val, exp = self._store[key]
                if exp > now: # Still valid
                    if nx:
                        return False
            expire_at = now + ex if ex else float("inf")
            self._store[key] = (str(value), expire_at)
            return True

    async def get(self, key: str) -> Optional[str]:
        async with self._lock:
            if key not in self._store:
                return None
            val, exp = self._store[key]
            if time.time() > exp:
                del self._store[key]
                return None
            return val

    async def delete(self, key: str) -> bool:
        async with self._lock:
            if key in self._store:
                del self._store[key]
                return True
            return False

    async def rpush(self, queue_name: str, item: str):
        async with self._lock:
            if queue_name not in self._queues:
                self._queues[queue_name] = []
            self._queues[queue_name].append(item)

    async def lpos(self, queue_name: str, item: str) -> Optional[int]:
        async with self._lock:
            q = self._queues.get(queue_name, [])
            try:
                return q.index(item)
            except ValueError:
                return None

    async def ping(self) -> bool:
        return True


class RedisService:
    def __init__(self):
        self.client = None
        self.fallback = InMemoryRedisFallback()
        self.is_connected = False

    async def initialize(self):
        try:
            client = aioredis.from_url(settings.REDIS_URL, decode_responses=True, socket_timeout=1.5)
            await client.ping()
            self.client = client
            self.is_connected = True
            logger.info("Connected to Redis server at %s", settings.REDIS_URL)
        except Exception as e:
            self.client = None
            self.is_connected = False
            logger.warning("Redis server unavailable (%s). Using high-concurrency in-memory cache/hold service.", e)

    async def acquire_slot_hold(self, slot_id: int, call_id: str, ttl: int = None) -> bool:
        """
        Soft-hold mechanism: LLM or Voice Intake requests a temporary slot reservation 
        using Redis TTL keys (e.g. 180 seconds) while conversational confirmation is completed.
        Uses NX (set if not exists) for atomic concurrency protection.
        """
        ttl = ttl or settings.SLOT_HOLD_TTL_SECONDS
        key = f"hold:slot:{slot_id}"
        if self.is_connected and self.client:
            try:
                # NX=True returns True only if key was set (i.e. not previously held)
                res = await self.client.set(key, call_id, ex=ttl, nx=True)
                return bool(res)
            except Exception as e:
                logger.error("Redis set error: %s, falling back to memory", e)
        
        return await self.fallback.set(key, call_id, ex=ttl, nx=True)

    async def get_slot_hold_caller(self, slot_id: int) -> Optional[str]:
        key = f"hold:slot:{slot_id}"
        if self.is_connected and self.client:
            try:
                return await self.client.get(key)
            except Exception:
                pass
        return await self.fallback.get(key)

    async def release_slot_hold(self, slot_id: int, call_id: str) -> bool:
        """
        Releases the hold only if the current holder is the specified call_id.
        """
        current_holder = await self.get_slot_hold_caller(slot_id)
        if current_holder == call_id:
            key = f"hold:slot:{slot_id}"
            if self.is_connected and self.client:
                try:
                    await self.client.delete(key)
                    return True
                except Exception:
                    pass
            return await self.fallback.delete(key)
        return False

    async def is_slot_held_by_other(self, slot_id: int, call_id: str) -> bool:
        holder = await self.get_slot_hold_caller(slot_id)
        if holder is None:
            return False
        return holder != call_id

    async def register_active_caller(self, call_id: str, department: str):
        queue_key = f"queue:dept:{department}"
        if self.is_connected and self.client:
            try:
                await self.client.rpush(queue_key, call_id)
                return
            except Exception:
                pass
        await self.fallback.rpush(queue_key, call_id)

    async def get_caller_queue_position(self, call_id: str, department: str) -> int:
        queue_key = f"queue:dept:{department}"
        pos = None
        if self.is_connected and self.client:
            try:
                pos = await self.client.lpos(queue_key, call_id)
            except Exception:
                pass
        if pos is None:
            pos = await self.fallback.lpos(queue_key, call_id)
        return (pos + 1) if pos is not None else 1

redis_service = RedisService()
