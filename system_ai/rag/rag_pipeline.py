import os
from typing import Any, Dict, List, Optional

from system_ai.memory.chroma_store import ChromaStore


class RagPipeline:
    def __init__(self, persist_dir: str = "~/.system_cli/chroma") -> None:
        self.persist_dir = os.path.expanduser(persist_dir)
        self.store = ChromaStore(persist_dir=persist_dir)
        # Enable via env var or automatically when an existing chroma persistence dir exists
        self.enabled = os.environ.get("SYSTEM_RAG_ENABLED", "0").lower() in {"1", "true", "yes", "on"}
        if not self.enabled:
            try:
                if os.path.isdir(self.persist_dir) and any(os.scandir(self.persist_dir)):
                    self.enabled = True
            except Exception:
                # Keep disabled on error
                pass

    def ingest_text(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> bool:
        if not self.enabled:
            return False
        return self.store.add_texts([text], metadatas=[metadata or {}])

    def retrieve(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        if not self.enabled:
            return []
        docs = self.store.similarity_search(query, k=k)
        out: List[Dict[str, Any]] = []
        for d in docs:
            try:
                out.append({"content": getattr(d, "page_content", ""), "metadata": getattr(d, "metadata", {})})
            except Exception:
                continue
        return out
