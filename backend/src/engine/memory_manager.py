"""
Hybrid Layered Memory Manager — coordinates all memory tiers.

Architecture:
  Working Memory (last 8 msgs) → Summary Memory (rolling) →
  Semantic Memory (pgvector) → Structured Memory (facts/prefs)

Usage:
  manager = MemoryManager(conversation_id, session)
  manager.add_message(role, content)
  context = manager.get_context()  # returns system prompt prefix
  results = await manager.search("what did we decide about deployment?")
"""

import json as _json
import uuid
from dataclasses import dataclass, field


@dataclass
class ContextBudget:
    """Track token usage across context components."""
    system_prompt: int = 0
    summary: int = 0
    working_memory: int = 0
    documents: int = 0
    retrieved: int = 0
    max_tokens: int = 8000  # leave room for output

    def total(self) -> int:
        return self.system_prompt + self.summary + self.working_memory + self.documents + self.retrieved

    def remaining(self) -> int:
        return max(0, self.max_tokens - self.total())

    def would_exceed(self, n: int) -> bool:
        return self.total() + n > self.max_tokens

    def report(self) -> str:
        return (
            f"Budget: {self.total()}/{self.max_tokens} tokens "
            f"(sys={self.system_prompt}, sum={self.summary}, "
            f"work={self.working_memory}, docs={self.documents}, ret={self.retrieved})"
        )


class MemoryManager:
    """Coordinates working, summary, semantic, and structured memory tiers."""

    def __init__(self, conversation_id: str, session=None):
        self.conversation_id = conversation_id
        self.session = session
        self.working: list[dict] = []
        self.summary: str = ""
        self.documents: list[dict] = []
        self.facts: list[dict] = []
        self.budget = ContextBudget()
        self._embedding_model = "text-embedding-3-small"
        self._fact_extract_interval = 5  # extract facts every N turns
        self._turn_count = 0

    def add_message(self, role: str, content: str):
        """Add a message to working memory. Auto-compact if over limit."""
        self.working.append({"role": role, "content": content})
        self._turn_count += 1
        if len(self.working) > 8:
            self._compact()

    def add_document(self, filename: str, preview: str):
        """Track document in session context."""
        self.documents.append({"filename": filename, "preview": preview[:300]})
        if len(self.documents) > 5:
            self.documents = self.documents[-5:]

    def _compact(self):
        """Move oldest messages to summary."""
        while len(self.working) > 8:
            old = self.working.pop(0)
            snippet = f"[{old['role']}]: {old['content'][:400]}"
            self.summary = (self.summary + "\n" + snippet)[-1500:]

    async def search(self, query: str, top_k: int = 5) -> list[dict]:
        """Semantic search over conversation history using pgvector."""
        if not self.session:
            return []
        from src.models.memory_embedding import HAS_VECTOR_DB

        if not HAS_VECTOR_DB:
            return []

        try:
            embedding = await self._embed(query)
            from sqlalchemy import text
            result = await self.session.execute(
                text("""
                    SELECT content, role, created_at,
                           1 - (embedding <=> :embedding) AS similarity
                    FROM memory_embeddings
                    WHERE conversation_id = :conv_id
                    ORDER BY embedding <=> :embedding
                    LIMIT :limit
                """),
                {"embedding": embedding, "conv_id": self.conversation_id, "limit": top_k},
            )
            return [
                {"content": row[0], "role": row[1], "similarity": round(float(row[3]), 3)}
                for row in result
            ]
        except Exception:
            return []

    async def store_embedding(self, role: str, content: str):
        """Generate and store embedding for a message."""
        if not self.session or len(content) < 20:
            return
        from src.models.memory_embedding import HAS_VECTOR_DB
        if not HAS_VECTOR_DB:
            return
        try:
            embedding = await self._embed(content[:2000])
            from src.models.memory_embedding import MemoryEmbedding, serialize_embedding
            emb = MemoryEmbedding(
                id=uuid.uuid4().hex[:16],
                conversation_id=self.conversation_id,
                content=content[:2000],
                role=role,
                embedding=serialize_embedding(embedding),
            )
            self.session.add(emb)
            await self.session.commit()
        except Exception:
            pass

    async def extract_facts(self):
        """LLM extracts structured facts from recent messages. Called every N turns."""
        if self._turn_count % self._fact_extract_interval != 0 or len(self.working) < 3:
            return
        try:
            from src.engine.llm import LLMMessage, LLMProvider
            llm = LLMProvider(default_model="gpt-4o-mini")
            recent = "\n".join(
                f"[{m['role']}]: {m['content'][:300]}" for m in self.working[-5:]
            )
            prompt = f"""Extract key facts from this conversation. Return JSON list.

Conversation:
{recent}

Return: [{{"type":"preference|decision|entity|constraint|goal","key":"...","value":"..."}}]"""
            resp = await llm.complete(
                messages=[LLMMessage(role="user", content=prompt)],
                system_prompt="Extract structured facts. Return JSON array only.",
                temperature=0.0, max_tokens=300,
            )
            facts = _json.loads(resp.content)
            for f in facts[:5]:
                self.facts.append(f)
                if self.session:
                    from src.models.memory_fact import MemoryFact
                    mf = MemoryFact(
                        id=uuid.uuid4().hex[:16],
                        conversation_id=self.conversation_id,
                        fact_type=f.get("type", "preference"),
                        key=f.get("key", ""),
                        value=f.get("value", ""),
                    )
                    self.session.add(mf)
            if self.session:
                await self.session.commit()
        except Exception:
            pass

    def get_context(self) -> str:
        """Build memory-augmented system prompt prefix."""
        parts = []
        if self.documents:
            docs = "\n".join(
                f"- **{d['filename']}**: {d['preview']}"
                for d in self.documents
            )
            parts.append(f"## Session Documents\n{docs}")
        if self.summary:
            parts.append(f"## Conversation Summary\n{self.summary}")
        if self.facts:
            facts = "\n".join(
                f"- [{f.get('type','fact')}] {f.get('key','')}: {f.get('value','')}"
                for f in self.facts[-10:]
            )
            parts.append(f"## Known Facts\n{facts}")
        return "\n\n".join(parts)

    async def _embed(self, text: str) -> list[float]:
        """Generate embedding via OpenAI."""
        import httpx
        import os
        key = os.environ.get("OPENAI_API_KEY", "")
        if not key:
            return [0.0] * 1536
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                "https://api.openai.com/v1/embeddings",
                headers={"Authorization": f"Bearer {key}"},
                json={"model": self._embedding_model, "input": text[:8000]},
            )
            data = resp.json()
            return data["data"][0]["embedding"]
