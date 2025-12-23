# Setting up ChromaDB for RAG ingestion

This project can index monitor summaries into ChromaDB for RAG retrieval. To enable this functionality:

1. Install dependencies (recommended via the helper script):

```bash
./scripts/setup_chroma.sh
```

2. Ensure the Chroma persist dir exists or set a custom path:

```bash
export SYSTEM_CHROMA_PERSIST_DIR="$HOME/.system_cli/chroma"
export SYSTEM_RAG_ENABLED=1
```

3. Verify ingestion works:

```python
from system_ai.rag.rag_pipeline import RagPipeline
rp = RagPipeline()
print('enabled', rp.enabled)
print('ingest', rp.ingest_text('test', metadata={'t':'m'}))
```

Note: If ingestion returns `False`, check that the Chroma client libraries are installed and functional.
