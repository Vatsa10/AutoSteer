import asyncio
import json
from collections.abc import Callable

import redis.asyncio as redis

from .schemas import AgentMessage


class MessageBus:
    def __init__(self, redis_url: str):
        self.redis = redis.from_url(redis_url)
        self._subscribers: dict[str, list[Callable]] = {}
        self._running = False

    async def publish(self, channel: str, message: AgentMessage):
        await self.redis.publish(channel, message.model_dump_json())

    async def subscribe(self, channel: str, callback: Callable):
        if channel not in self._subscribers:
            self._subscribers[channel] = []
        self._subscribers[channel].append(callback)

    async def start_listening(self):
        if not self._subscribers:
            return
        self._running = True
        pubsub = self.redis.pubsub()
        await pubsub.subscribe(*self._subscribers.keys())
        loop = asyncio.get_running_loop()
        while self._running:
            try:
                message = await loop.run_in_executor(
                    None, lambda: pubsub.get_message(timeout=1.0)
                )
                if message is None or message["type"] != "message":
                    continue
                channel = message["channel"]
                if isinstance(channel, bytes):
                    channel = channel.decode()
                data = message["data"]
                if isinstance(data, bytes):
                    data = data.decode()
                agent_message = AgentMessage.model_validate_json(data)
                for callback in self._subscribers.get(channel, []):
                    await callback(agent_message)
            except Exception:
                await asyncio.sleep(0.5)

    async def close(self):
        self._running = False
        await self.redis.aclose()
