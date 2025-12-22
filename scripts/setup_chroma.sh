#!/usr/bin/env bash
set -euo pipefail

echo "Installing Chroma and required libs..."
python3 -m pip install --upgrade pip
python3 -m pip install chromadb langchain_chroma langchain_huggingface sentence-transformers

echo "Chroma install complete. To enable RAG ingestion set: SYSTEM_RAG_ENABLED=1"
echo "If you want to change the persist dir, set SYSTEM_CHROMA_PERSIST_DIR to the path."
